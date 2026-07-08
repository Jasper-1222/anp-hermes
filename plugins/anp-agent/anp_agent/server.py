"""ANP HTTP 端点服务器。

提供 ANP 服务智能体所需的核心端点：
- GET /agent/ad.json      Agent Description，用于 RemoteAgent.discover()
- GET /.well-known/agent-descriptions  主动发现 CollectionPage
- GET /agent/interface.json  OpenRPC 接口描述
- POST /agent/rpc         JSON-RPC 2.0 调用入口

本模块仅依赖 ANP 插件内部模块与 aiohttp，不调用 Hermes 未公开 API。
"""

import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_app import AppKey

from .auth import ANPAuth, AuthenticationError
from .bridge import ANPBridge, ANPBridgeError
from .config import ANPConfig
from .identity import ANPIdentity
from .tools import (
    ToolInvoker,
    ToolListProvider,
    ToolRPCDispatcher,
    ToolRPCError,
    invoke_hermes_tool,
    list_hermes_tools,
    rpc_method_for_tool,
    tool_name_from_rpc_method,
)

logger = logging.getLogger(__name__)

# aiohttp 应用配置键（推荐用法，避免 NotAppKeyWarning）
_CONFIG_KEY: AppKey[ANPConfig] = AppKey("anp_config", ANPConfig)
_IDENTITY_KEY: AppKey[ANPIdentity] = AppKey("anp_identity", ANPIdentity)
_AUTH_KEY: AppKey[ANPAuth] = AppKey("anp_auth", ANPAuth)
_BRIDGE_KEY: AppKey[ANPBridge] = AppKey("anp_bridge", ANPBridge)
_TOOLS_KEY: AppKey[ToolRPCDispatcher] = AppKey("anp_tools", ToolRPCDispatcher)

# JSON-RPC 2.0 标准错误码
_ERROR_PARSE = -32700
_ERROR_INVALID_REQUEST = -32600
_ERROR_METHOD_NOT_FOUND = -32601
_ERROR_INTERNAL = -32603

# ANP Core Binding public error codes
_ERROR_UNSUPPORTED_PROFILE = 1001
_ERROR_UNSUPPORTED_SECURITY_PROFILE = 1002
_ERROR_INVALID_PARAMS_SHAPE = 1003

# ANP Core Binding 支持能力
_CORE_PROFILE = "anp.core.binding.v1"
_SECURITY_PROFILE_TRANSPORT = "transport-protected"
_SUPPORTED_PROFILES = [_CORE_PROFILE]
_SUPPORTED_SECURITY_PROFILES = [_SECURITY_PROFILE_TRANSPORT]
_SUPPORTED_CONTENT_TYPES = ["text/plain", "application/json"]

# ANP 插件自定义认证错误码
_ERROR_INVALID_SIGNATURE = -32001
_ERROR_DID_UNRESOLVABLE = -32002


class ANPRPCError(Exception):
    """JSON-RPC 处理错误，携带 HTTP 状态码与 JSON-RPC 错误码。"""

    def __init__(
        self,
        http_status: int,
        rpc_code: int,
        message: str,
        rpc_id: Any = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.http_status = http_status
        self.rpc_code = rpc_code
        self.message = message
        self.rpc_id = rpc_id
        self.data = data
        super().__init__(message)


def _jsonrpc_error(
    rpc_id: Any,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造 JSON-RPC 2.0 error 响应体。"""
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": error,
    }


def _jsonrpc_result(rpc_id: Any, result: Any) -> dict[str, Any]:
    """构造 JSON-RPC 2.0 result 响应体。"""
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _tool_methods(tools: ToolRPCDispatcher | None) -> list[str]:
    """返回当前已暴露 Hermes tool 的 RPC method 名称。"""
    if tools is None:
        return []
    return [rpc_method_for_tool(tool.name) for tool in tools.exposed_tools()]


def _build_ad_json(
    config: ANPConfig,
    identity: ANPIdentity,
    tools: ToolRPCDispatcher | None = None,
) -> dict[str, Any]:
    """构造 Agent Description JSON。"""
    endpoint = config.endpoint
    ad_url = f"{endpoint}/agent/ad.json"
    tool_methods = _tool_methods(tools)
    ad = {
        "protocolType": "ANP",
        "protocolVersion": "1.0.0",
        "type": "AgentDescription",
        "url": ad_url,
        "name": "Hermes ANP Agent",
        "description": "基于 Hermes 的 ANP 服务智能体参考实现，支持 chat 方法。",
        "endpoint": endpoint,
        "interfaces": [
            {
                "type": "StructuredInterface",
                "protocol": "openrpc",
                "url": f"{endpoint}/agent/interface.json",
            }
        ],
        "id": identity.did,
        "did": identity.did,
        "securityDefinitions": {
            "didwba_sc": {
                "scheme": "didwba",
                "in": "header",
                "name": "Authorization",
            }
        },
        "security": "didwba_sc",
    }
    if tool_methods:
        ad["capabilities"] = {"hermes_tools": tool_methods}
    return ad


def _build_agent_descriptions_collection(
    config: ANPConfig,
    identity: ANPIdentity,
    tools: ToolRPCDispatcher | None = None,
) -> dict[str, Any]:
    """构造 ANP 主动发现 CollectionPage。"""
    endpoint = config.endpoint
    ad = _build_ad_json(config, identity, tools)
    return {
        "@context": {
            "@vocab": "https://schema.org/",
            "did": "https://w3id.org/did#",
            "ad": "https://agent-network-protocol.com/ad#",
        },
        "@type": "CollectionPage",
        "url": f"{endpoint}/.well-known/agent-descriptions",
        "items": [
            {
                "@type": "ad:AgentDescription",
                "name": ad["name"],
                "@id": ad["url"],
                "did": identity.did,
            }
        ],
    }


def _tool_openrpc_methods(tools: ToolRPCDispatcher | None) -> list[dict[str, Any]]:
    """将当前可暴露工具转换为 OpenRPC methods。"""
    if tools is None:
        return []
    methods = []
    for tool in tools.exposed_tools():
        methods.append(
            {
                "name": rpc_method_for_tool(tool.name),
                "summary": f"调用 Hermes tool: {tool.name}",
                "description": tool.description or f"执行 allowlisted Hermes tool {tool.name}",
                "params": [
                    {
                        "name": "params",
                        "description": "Hermes tool 参数对象。",
                        "schema": tool.schema,
                        "required": True,
                    }
                ],
                "result": {
                    "name": "result",
                    "description": "Hermes tool 返回内容与安全元数据。",
                    "schema": {"type": "object"},
                },
            }
        )
    return methods


def _build_openrpc_json(
    config: ANPConfig,
    tools: ToolRPCDispatcher | None = None,
) -> dict[str, Any]:
    """构造 OpenRPC 接口文档，声明当前方法。"""
    endpoint = config.endpoint
    methods = [
        {
            "name": "chat",
            "summary": "与 Hermes 智能体进行单轮文本对话",
            "description": "与 Hermes 智能体进行单轮文本对话，支持 legacy params.message 与 ANP Core Binding params.body.message。",
            "params": [
                {
                    "name": "params",
                    "description": "legacy 形态可传 {message}；Core Binding 形态可传 {meta, body: {message}}。",
                    "schema": {
                        "type": "object",
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {"message": {"type": "string"}},
                                "required": ["message"],
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "meta": {"type": "object"},
                                    "body": {
                                        "type": "object",
                                        "properties": {"message": {"type": "string"}},
                                        "required": ["message"],
                                    },
                                },
                                "required": ["meta", "body"],
                            },
                        ],
                    },
                    "required": True,
                }
            ],
            "result": {
                "name": "response",
                "description": "Hermes 智能体生成的回复文本",
                "schema": {"type": "string"},
            },
        },
        {
            "name": "anp.get_capabilities",
            "summary": "获取当前运行时 ANP 能力",
            "description": "返回服务 DID、支持的 ANP profiles、安全 profiles、实现限制与内容类型。",
            "params": [
                {
                    "name": "params",
                    "description": "ANP Core Binding envelope，body 可为空对象。",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "meta": {"type": "object"},
                            "body": {"type": "object"},
                        },
                        "required": ["meta", "body"],
                    },
                    "required": False,
                }
            ],
            "result": {
                "name": "capabilities",
                "description": "当前运行时 ANP 能力声明",
                "schema": {"type": "object"},
            },
        },
    ]
    methods.extend(_tool_openrpc_methods(tools))
    return {
        "openrpc": "1.3.2",
        "info": {
            "title": "Hermes ANP Agent OpenRPC",
            "version": "1.0.0",
            "description": "ANP JSON-RPC 接口文档。",
        },
        "servers": [
            {
                "name": "anp-agent",
                "url": f"{endpoint}/agent/rpc",
            }
        ],
        "methods": methods,
        "components": {
            "schemas": {},
            "links": {},
            "errors": {},
        },
    }


async def _handle_did_json(request: web.Request) -> web.Response:
    """GET /agent/did.json 处理器（ANP DID 文档解析所需）。"""
    identity: ANPIdentity = request.app[_IDENTITY_KEY]
    return web.json_response(identity.did_document)


async def _handle_ad_json(request: web.Request) -> web.Response:
    """GET /agent/ad.json 处理器。"""
    config: ANPConfig = request.app[_CONFIG_KEY]
    identity: ANPIdentity = request.app[_IDENTITY_KEY]
    tools: ToolRPCDispatcher = request.app[_TOOLS_KEY]
    return web.json_response(_build_ad_json(config, identity, tools))


async def _handle_agent_descriptions(request: web.Request) -> web.Response:
    """GET /.well-known/agent-descriptions 处理器。"""
    config: ANPConfig = request.app[_CONFIG_KEY]
    identity: ANPIdentity = request.app[_IDENTITY_KEY]
    tools: ToolRPCDispatcher = request.app[_TOOLS_KEY]
    return web.json_response(_build_agent_descriptions_collection(config, identity, tools))


async def _handle_interface_json(request: web.Request) -> web.Response:
    """GET /agent/interface.json 处理器。"""
    config: ANPConfig = request.app[_CONFIG_KEY]
    tools: ToolRPCDispatcher = request.app[_TOOLS_KEY]
    return web.json_response(_build_openrpc_json(config, tools))


def _extract_request_url(request: web.Request) -> str:
    """根据请求重建完整 URL（不含 query string，与签名一致）。"""
    # 使用 config.endpoint 中的 scheme/host 与请求路径拼接，
    # 保证端口 0 或反向代理场景下 URL 与签名目标一致。
    config: ANPConfig = request.app[_CONFIG_KEY]
    base = config.endpoint.rstrip("/")
    return f"{base}{request.path}"


async def _parse_rpc_request(request: web.Request) -> tuple[str, str, dict[str, Any]]:
    """解析并校验 JSON-RPC 请求体。

    Returns:
        (rpc_id, method, params)

    Raises:
        ANPRPCError: 解析失败或缺少必要字段。
    """
    try:
        body_bytes = await request.read()
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_PARSE,
            message="请求体不是合法 UTF-8",
        ) from exc

    try:
        data = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_PARSE,
            message="JSON 解析失败",
        ) from exc

    if not isinstance(data, dict):
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="JSON-RPC 请求必须是对象",
        )

    rpc_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})
    response_id = rpc_id if isinstance(rpc_id, str) and rpc_id else None

    if data.get("jsonrpc") != "2.0":
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="jsonrpc 必须是 2.0",
            rpc_id=response_id,
        )

    if not isinstance(rpc_id, str) or not rpc_id:
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="id 必须是非空字符串",
        )

    if method is None:
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="缺少 method 字段",
            rpc_id=rpc_id,
        )

    if not isinstance(method, str):
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="method 必须是字符串",
            rpc_id=rpc_id,
        )

    if not isinstance(params, dict):
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="params 必须是对象",
            rpc_id=rpc_id,
        )

    return rpc_id, method, params


def _anp_error_data(anp_code: str, retryable: bool = False) -> dict[str, Any]:
    """构造 ANP Core Binding 机器可读错误数据。"""
    return {"anp_code": anp_code, "retryable": retryable, "details": {}}


def _is_core_binding_envelope(params: dict[str, Any]) -> bool:
    """判断 params 是否采用 Core Binding meta/body envelope。"""
    return "meta" in params or "body" in params


def _validate_core_binding_params(params: dict[str, Any]) -> None:
    """校验最小 Core Binding params envelope。"""
    meta = params.get("meta")
    body = params.get("body")
    if not isinstance(meta, dict) or not isinstance(body, dict):
        raise ANPRPCError(
            http_status=200,
            rpc_code=_ERROR_INVALID_PARAMS_SHAPE,
            message="params.meta 和 params.body 必须是对象",
            data=_anp_error_data("anp.invalid_params_shape"),
        )

    profile = meta.get("profile")
    if profile != _CORE_PROFILE:
        raise ANPRPCError(
            http_status=200,
            rpc_code=_ERROR_UNSUPPORTED_PROFILE,
            message="不支持的 ANP profile",
            data=_anp_error_data("anp.unsupported_profile"),
        )

    security_profile = meta.get("security_profile")
    if security_profile != _SECURITY_PROFILE_TRANSPORT:
        raise ANPRPCError(
            http_status=200,
            rpc_code=_ERROR_UNSUPPORTED_SECURITY_PROFILE,
            message="不支持的 ANP security profile",
            data=_anp_error_data("anp.unsupported_security_profile"),
        )


def _extract_chat_params(params: dict[str, Any]) -> dict[str, Any]:
    """提取 chat 方法传给 bridge 的参数。"""
    if _is_core_binding_envelope(params):
        _validate_core_binding_params(params)
        body = params["body"]
        if "message" in body:
            return {**params, "message": body["message"]}
    return params


def _build_capabilities(
    identity: ANPIdentity,
    tools: ToolRPCDispatcher | None = None,
) -> dict[str, Any]:
    """构造 ANP Core Binding 运行时能力。"""
    result: dict[str, Any] = {
        "service_did": identity.did,
        "supported_profiles": _SUPPORTED_PROFILES,
        "supported_security_profiles": _SUPPORTED_SECURITY_PROFILES,
        "limits": {"max_request_bytes": str(_MAX_REQUEST_BODY_SIZE)},
        "supported_content_types": _SUPPORTED_CONTENT_TYPES,
    }
    tool_methods = _tool_methods(tools)
    if tool_methods:
        result["hermes_tools"] = tool_methods
    return result


def _validate_capabilities_params(params: dict[str, Any]) -> None:
    """校验 anp.get_capabilities 的 Core Binding params。"""
    if _is_core_binding_envelope(params):
        _validate_core_binding_params(params)


def _map_auth_error(
    exc: AuthenticationError,
) -> tuple[ANPRPCError, dict[str, str] | None]:
    """将结构化认证异常映射为 JSON-RPC / HTTP 错误。

    直接读取 AuthenticationError 携带的元数据，不再反向解析异常字符串。
    """
    challenge_headers: dict[str, str] | None = None
    if exc.status_code == 401 and exc.headers:
        challenge_headers = {
            name: value
            for name, value in exc.headers.items()
            if name.lower() in ("www-authenticate", "accept-signature")
        }

    return (
        ANPRPCError(
            http_status=exc.status_code,
            rpc_code=exc.rpc_code,
            message=str(exc),
        ),
        challenge_headers,
    )


# 请求体大小限制：1MB，避免大请求耗尽内存
_MAX_REQUEST_BODY_SIZE = 1024 * 1024


async def _handle_rpc(request: web.Request) -> web.Response:
    """POST /agent/rpc 处理器。"""
    auth: ANPAuth = request.app[_AUTH_KEY]
    bridge: ANPBridge = request.app[_BRIDGE_KEY]
    identity: ANPIdentity = request.app[_IDENTITY_KEY]
    tools: ToolRPCDispatcher = request.app[_TOOLS_KEY]

    # 1. 解析 JSON-RPC 请求
    try:
        rpc_id, method, params = await _parse_rpc_request(request)
    except ANPRPCError as exc:
        return web.json_response(
            _jsonrpc_error(exc.rpc_id, exc.rpc_code, exc.message, exc.data),
            status=exc.http_status,
        )

    # 2. 认证调用方
    try:
        url = _extract_request_url(request)
        body = await request.text()
        headers = dict(request.headers)
        auth_result = await auth.authenticate(request.method, url, headers, body)
    except AuthenticationError as exc:
        err, challenge_headers = _map_auth_error(exc)
        return web.json_response(
            _jsonrpc_error(rpc_id, err.rpc_code, err.message),
            status=err.http_status,
            headers=challenge_headers,
        )

    # 3. 方法路由
    if method == "anp.get_capabilities":
        try:
            _validate_capabilities_params(params)
        except ANPRPCError as exc:
            return web.json_response(
                _jsonrpc_error(rpc_id, exc.rpc_code, exc.message, exc.data),
                status=exc.http_status,
            )
        return web.json_response(
            _jsonrpc_result(rpc_id, _build_capabilities(identity, tools)),
            status=200,
            headers=auth_result.headers or None,
        )

    tool_name = tool_name_from_rpc_method(method)
    if tool_name is not None:
        try:
            tool_result = await tools.call_tool(
                caller_did=auth_result.caller_did,
                rpc_id=rpc_id,
                request_id=rpc_id,
                tool_name=tool_name,
                params=params,
            )
        except ToolRPCError as exc:
            return web.json_response(
                _jsonrpc_error(rpc_id, exc.rpc_code, exc.message, exc.data),
                status=200,
            )
        return web.json_response(
            _jsonrpc_result(rpc_id, tool_result),
            status=200,
            headers=auth_result.headers or None,
        )

    if method != "chat":
        return web.json_response(
            _jsonrpc_error(rpc_id, _ERROR_METHOD_NOT_FOUND, f"方法不存在: {method}"),
            status=200,
        )

    try:
        bridge_params = _extract_chat_params(params)
    except ANPRPCError as exc:
        return web.json_response(
            _jsonrpc_error(rpc_id, exc.rpc_code, exc.message, exc.data),
            status=exc.http_status,
        )

    # 4. 调用桥接层
    try:
        result_text = await bridge.call(rpc_id, method, bridge_params, auth_result.caller_did)
    except ANPBridgeError as exc:
        return web.json_response(
            _jsonrpc_error(rpc_id, exc.rpc_code, exc.message),
            status=200,
        )
    except Exception as exc:
        logger.exception("bridge.call 调用失败: %s", exc)
        return web.json_response(
            _jsonrpc_error(rpc_id, _ERROR_INTERNAL, "请求处理过程中发生内部错误"),
            status=200,
        )

    return web.json_response(
        _jsonrpc_result(rpc_id, {"response": result_text}),
        status=200,
        headers=auth_result.headers or None,
    )


def create_app(
    config: ANPConfig,
    identity: ANPIdentity,
    auth: ANPAuth,
    bridge: ANPBridge,
    list_tools: ToolListProvider = list_hermes_tools,
    invoke_tool: ToolInvoker = invoke_hermes_tool,
) -> web.Application:
    """创建并返回配置好的 aiohttp Application。

    Args:
        config: ANP 插件配置。
        identity: 服务端 DID WBA 身份。
        auth: DID WBA 认证器。
        bridge: ANP-Hermes RPC 桥接器。

    Returns:
        aiohttp web.Application 实例。
    """
    app = web.Application(client_max_size=_MAX_REQUEST_BODY_SIZE)
    app[_CONFIG_KEY] = config
    app[_IDENTITY_KEY] = identity
    app[_AUTH_KEY] = auth
    app[_BRIDGE_KEY] = bridge
    app[_TOOLS_KEY] = ToolRPCDispatcher(
        config.tool_rpc,
        list_tools=list_tools,
        invoke_tool=invoke_tool,
    )

    app.router.add_get("/agent/ad.json", _handle_ad_json)
    app.router.add_get("/.well-known/agent-descriptions", _handle_agent_descriptions)
    app.router.add_get("/agent/interface.json", _handle_interface_json)
    app.router.add_post("/agent/rpc", _handle_rpc)

    # 注册 DID 文档端点：根据 DID 的 path segments 动态构造路径
    did_parts = identity.did.split(":")
    if len(did_parts) >= 4:
        path_segments = did_parts[3:]
        did_route_path = "/" + "/".join(path_segments) + "/did.json"
    else:
        did_route_path = "/agent/did.json"
    app.router.add_get(did_route_path, _handle_did_json)

    logger.info("ANP HTTP 服务器路由已注册: %s", list(app.router.keys()))
    return app
