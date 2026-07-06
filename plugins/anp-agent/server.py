"""ANP HTTP 端点服务器。

提供 ANP 服务智能体所需的三个核心端点：
- GET /agent/ad.json      Agent Description，用于 RemoteAgent.discover()
- GET /agent/interface.json  OpenRPC 接口描述
- POST /agent/rpc         JSON-RPC 2.0 调用入口

本模块仅依赖 ANP 插件内部模块与 aiohttp，不调用 Hermes 未公开 API。
"""

import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_app import AppKey

from auth import ANPAuth, AuthenticationError
from bridge import ANPBridge
from config import ANPConfig
from identity import ANPIdentity

logger = logging.getLogger(__name__)

# aiohttp 应用配置键（推荐用法，避免 NotAppKeyWarning）
_CONFIG_KEY: AppKey[ANPConfig] = AppKey("anp_config", ANPConfig)
_IDENTITY_KEY: AppKey[ANPIdentity] = AppKey("anp_identity", ANPIdentity)
_AUTH_KEY: AppKey[ANPAuth] = AppKey("anp_auth", ANPAuth)
_BRIDGE_KEY: AppKey[ANPBridge] = AppKey("anp_bridge", ANPBridge)

# JSON-RPC 2.0 标准错误码
_ERROR_PARSE = -32700
_ERROR_INVALID_REQUEST = -32600
_ERROR_METHOD_NOT_FOUND = -32601
_ERROR_INTERNAL = -32603

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
    ) -> None:
        self.http_status = http_status
        self.rpc_code = rpc_code
        self.message = message
        self.rpc_id = rpc_id
        super().__init__(message)


def _jsonrpc_error(rpc_id: Any, code: int, message: str) -> dict[str, Any]:
    """构造 JSON-RPC 2.0 error 响应体。"""
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_result(rpc_id: Any, result: Any) -> dict[str, Any]:
    """构造 JSON-RPC 2.0 result 响应体。"""
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _build_ad_json(config: ANPConfig, identity: ANPIdentity) -> dict[str, Any]:
    """构造 Agent Description JSON。"""
    endpoint = config.endpoint
    return {
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
    }


def _build_openrpc_json(config: ANPConfig) -> dict[str, Any]:
    """构造 OpenRPC 接口文档，声明 chat 方法。"""
    endpoint = config.endpoint
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
        "methods": [
            {
                "name": "chat",
                "summary": "与 Hermes 智能体进行单轮文本对话",
                "description": "与 Hermes 智能体进行单轮文本对话，接收 message 参数并返回 response 文本。",
                "params": [
                    {
                        "name": "message",
                        "description": "用户输入的文本消息",
                        "schema": {"type": "string"},
                        "required": True,
                    }
                ],
                "result": {
                    "name": "response",
                    "description": "Hermes 智能体生成的回复文本",
                    "schema": {"type": "string"},
                },
            }
        ],
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
    return web.json_response(_build_ad_json(config, identity))


async def _handle_interface_json(request: web.Request) -> web.Response:
    """GET /agent/interface.json 处理器。"""
    config: ANPConfig = request.app[_CONFIG_KEY]
    return web.json_response(_build_openrpc_json(config))


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

    if rpc_id is None or method is None:
        raise ANPRPCError(
            http_status=400,
            rpc_code=_ERROR_INVALID_REQUEST,
            message="缺少 jsonrpc id 或 method 字段",
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

    # 1. 解析 JSON-RPC 请求
    try:
        rpc_id, method, params = await _parse_rpc_request(request)
    except ANPRPCError as exc:
        return web.json_response(
            _jsonrpc_error(exc.rpc_id, exc.rpc_code, exc.message),
            status=exc.http_status,
        )

    # 2. 认证调用方
    try:
        url = _extract_request_url(request)
        body = await request.text()
        headers = dict(request.headers)
        caller_did = await auth.authenticate(request.method, url, headers, body)
    except AuthenticationError as exc:
        err, challenge_headers = _map_auth_error(exc)
        return web.json_response(
            _jsonrpc_error(rpc_id, err.rpc_code, err.message),
            status=err.http_status,
            headers=challenge_headers,
        )

    # 3. 方法路由
    if method != "chat":
        return web.json_response(
            _jsonrpc_error(rpc_id, _ERROR_METHOD_NOT_FOUND, f"方法不存在: {method}"),
            status=200,
        )

    # 4. 调用桥接层
    try:
        result_text = await bridge.call(rpc_id, method, params, caller_did)
    except Exception as exc:
        logger.exception("bridge.call 调用失败: %s", exc)
        return web.json_response(
            _jsonrpc_error(rpc_id, _ERROR_INTERNAL, "请求处理过程中发生内部错误"),
            status=200,
        )

    return web.json_response(
        _jsonrpc_result(rpc_id, {"response": result_text}),
        status=200,
    )


def create_app(
    config: ANPConfig,
    identity: ANPIdentity,
    auth: ANPAuth,
    bridge: ANPBridge,
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

    app.router.add_get("/agent/ad.json", _handle_ad_json)
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
