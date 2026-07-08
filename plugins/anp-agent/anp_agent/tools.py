"""Hermes tools 通过 ANP RPC 暴露的安全策略。"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .config import ToolRPCConfig

RPC_METHOD_PREFIX = "hermes.tool."

HIGH_RISK_TOOL_DENYLIST = frozenset(
    {
        "terminal",
        "execute_code",
        "write_file",
        "patch",
        "skill_manage",
        "browser_click",
        "browser_type",
        "browser_file_upload",
        "browser_run_code_unsafe",
    }
)


@dataclass(frozen=True)
class ToolDefinition:
    """可暴露 Hermes tool 的最小定义。"""

    name: str
    toolset: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    description: str = ""


class ToolRPCError(Exception):
    """工具 RPC 结构化错误。"""

    def __init__(
        self,
        message: str,
        rpc_code: int = -32603,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.rpc_code = rpc_code
        self.data = data
        super().__init__(message)


class ToolRPCMethodNotFoundError(ToolRPCError):
    """工具 RPC method 不存在或未授权。"""

    def __init__(self, message: str = "方法不存在") -> None:
        super().__init__(message, rpc_code=-32601)


class ToolRPCInvalidParamsError(ToolRPCError):
    """工具 RPC 参数无效。"""

    def __init__(self, message: str = "工具参数无效") -> None:
        super().__init__(message, rpc_code=-32602)


class ToolRPCTimeoutError(ToolRPCError):
    """工具 RPC 执行超时。"""

    def __init__(self) -> None:
        super().__init__(
            "工具执行超时",
            rpc_code=-32603,
            data={"anp_code": "anp.tool_timeout", "retryable": True, "details": {}},
        )


class ToolRPCResultTooLargeError(ToolRPCError):
    """工具 RPC 结果过大。"""

    def __init__(self) -> None:
        super().__init__(
            "工具结果过大",
            rpc_code=-32603,
            data={
                "anp_code": "anp.tool_result_too_large",
                "retryable": False,
                "details": {},
            },
        )


class ToolRPCInvocationFailedError(ToolRPCError):
    """工具 RPC 执行失败。"""

    def __init__(self) -> None:
        super().__init__(
            "工具执行失败",
            rpc_code=-32603,
            data={"anp_code": "anp.tool_failed", "retryable": False, "details": {}},
        )


def rpc_method_for_tool(tool_name: str) -> str:
    """将 Hermes registry tool name 映射为 ANP JSON-RPC method。"""
    return f"{RPC_METHOD_PREFIX}{tool_name}"


def tool_name_from_rpc_method(method: str) -> str | None:
    """从 `hermes.tool.*` JSON-RPC method 中提取 Hermes tool name。"""
    if not method.startswith(RPC_METHOD_PREFIX):
        return None
    tool_name = method[len(RPC_METHOD_PREFIX) :]
    return tool_name or None


class ToolExposurePolicy:
    """根据配置判断 Hermes tool 是否可通过 ANP 暴露。"""

    def __init__(self, config: ToolRPCConfig) -> None:
        self._config = config

    def exposed_tools(self, tools: list[ToolDefinition]) -> list[ToolDefinition]:
        """返回当前配置允许向 ANP 声明的工具列表。"""
        if not self._config.enabled or not self._config.has_allowlist:
            return []
        return [tool for tool in tools if self._is_tool_allowed(tool)]

    def require_tool(
        self,
        caller_did: str,
        tool_name: str,
        tools: list[ToolDefinition],
    ) -> ToolDefinition:
        """校验 caller DID 与工具策略，返回可执行工具定义。"""
        if not self._is_caller_allowed(caller_did):
            raise ToolRPCMethodNotFoundError()
        for tool in self.exposed_tools(tools):
            if tool.name == tool_name:
                return tool
        raise ToolRPCMethodNotFoundError()

    def _is_caller_allowed(self, caller_did: str) -> bool:
        """判断 caller DID 是否允许调用 tool RPC。"""
        if not self._config.enabled or not self._config.has_allowlist:
            return False
        return caller_did in self._config.allowed_dids

    def _is_tool_allowed(self, tool: ToolDefinition) -> bool:
        """判断单个工具是否通过 allowlist 与 denylist。"""
        denied = set(self._config.denied_tools) | set(HIGH_RISK_TOOL_DENYLIST)
        if tool.name in denied:
            return False
        if tool.name in self._config.allowed_tools:
            return True
        return bool(tool.toolset and tool.toolset in self._config.allowed_toolsets)


ToolListProvider = Callable[[], list[ToolDefinition]]
ToolInvoker = Callable[..., Any | Awaitable[Any]]
AuditSink = Callable[[dict[str, Any]], None]


def list_hermes_tools() -> list[ToolDefinition]:
    """从 Hermes 高层工具定义入口读取当前可用工具；不可用时返回空列表。"""
    try:
        from model_tools import get_tool_definitions
    except Exception:
        return []

    try:
        definitions = get_tool_definitions(
            enabled_toolsets=None,
            disabled_toolsets=None,
            quiet_mode=True,
            skip_tool_search_assembly=True,
        )
    except TypeError:
        definitions = get_tool_definitions(None, None, True)
    except Exception:
        return []

    tools: list[ToolDefinition] = []
    for item in definitions or []:
        function = item.get("function", {}) if isinstance(item, dict) else {}
        name = function.get("name")
        if not name:
            continue
        tools.append(
            ToolDefinition(
                name=str(name),
                toolset=str(function.get("toolset") or ""),
                schema=function.get("parameters") or {},
                description=str(function.get("description") or ""),
            )
        )
    return tools


async def invoke_hermes_tool(tool_name: str, params: dict[str, Any], **kwargs: Any) -> Any:
    """通过 Hermes 高层工具调用入口执行工具。"""
    try:
        from model_tools import handle_function_call
    except Exception as exc:  # pragma: no cover - 仅在非 Hermes 环境触发
        raise RuntimeError("Hermes tool invocation is unavailable") from exc

    request_id = str(kwargs.get("request_id") or "anp-tool")
    result = await asyncio.to_thread(
        handle_function_call,
        tool_name,
        params,
        request_id,
        "ANP tool RPC",
    )
    return result


class ToolRPCDispatcher:
    """受控执行 allowlisted Hermes tool 的调度器。"""

    def __init__(
        self,
        config: ToolRPCConfig,
        list_tools: ToolListProvider,
        invoke_tool: ToolInvoker,
        audit: AuditSink | None = None,
    ) -> None:
        self._config = config
        self._policy = ToolExposurePolicy(config)
        self._list_tools = list_tools
        self._invoke_tool = invoke_tool
        self._audit = audit

    def exposed_tools(self) -> list[ToolDefinition]:
        """返回当前可声明的工具。"""
        return self._policy.exposed_tools(self._list_tools())

    async def call_tool(
        self,
        *,
        caller_did: str,
        rpc_id: str,
        request_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """校验并执行单个 Hermes tool。"""
        started = time.monotonic()
        status = "success"
        error_category: str | None = None
        try:
            tool = self._policy.require_tool(caller_did, tool_name, self._list_tools())
            _validate_params(tool.schema, params)
            try:
                result = await asyncio.wait_for(
                    _maybe_await(
                        self._invoke_tool(
                            tool_name,
                            params,
                            caller_did=caller_did,
                            rpc_id=rpc_id,
                            request_id=request_id,
                        )
                    ),
                    timeout=max(0.001, self._config.timeout_seconds),
                )
            except asyncio.TimeoutError as exc:
                status = "failure"
                error_category = "timeout"
                raise ToolRPCTimeoutError() from exc
            except Exception as exc:
                status = "failure"
                error_category = "failed"
                raise ToolRPCInvocationFailedError() from exc

            result_size = len(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8"))
            if result_size > self._config.max_result_bytes:
                status = "failure"
                error_category = "result_too_large"
                raise ToolRPCResultTooLargeError()
            return {
                "content": result,
                "tool": tool_name,
                "metadata": {"request_id": request_id},
            }
        except ToolRPCError as exc:
            status = "failure"
            if error_category is None:
                error_category = exc.data.get("anp_code", "error") if exc.data else "error"
            raise
        finally:
            self._record_audit(
                caller_did=caller_did,
                rpc_id=rpc_id,
                request_id=request_id,
                tool_name=tool_name,
                status=status,
                error_category=error_category,
                started=started,
            )

    def _record_audit(
        self,
        *,
        caller_did: str,
        rpc_id: str,
        request_id: str,
        tool_name: str,
        status: str,
        error_category: str | None,
        started: float,
    ) -> None:
        """记录不含完整参数和结果的安全审计事件。"""
        if self._audit is None:
            return
        event: dict[str, Any] = {
            "caller_did": caller_did,
            "rpc_id": rpc_id,
            "request_id": request_id,
            "tool": tool_name,
            "status": status,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
        if error_category is not None:
            event["error_category"] = error_category
        self._audit(event)


def _validate_params(schema: dict[str, Any], params: dict[str, Any]) -> None:
    """执行最小 JSON Schema 参数校验。"""
    required = schema.get("required", [])
    for name in required:
        if name not in params:
            raise ToolRPCInvalidParamsError(f"缺少必填参数: {name}")

    properties = schema.get("properties", {})
    for name, value in params.items():
        expected = properties.get(name, {}).get("type")
        if expected == "string" and not isinstance(value, str):
            raise ToolRPCInvalidParamsError(f"参数类型无效: {name}")
        if expected == "object" and not isinstance(value, dict):
            raise ToolRPCInvalidParamsError(f"参数类型无效: {name}")
        if expected == "array" and not isinstance(value, list):
            raise ToolRPCInvalidParamsError(f"参数类型无效: {name}")
        if expected == "boolean" and not isinstance(value, bool):
            raise ToolRPCInvalidParamsError(f"参数类型无效: {name}")
        if expected in {"integer", "number"} and not isinstance(value, int | float):
            raise ToolRPCInvalidParamsError(f"参数类型无效: {name}")


async def _maybe_await(value: Any | Awaitable[Any]) -> Any:
    """等待 awaitable，普通值直接返回。"""
    if hasattr(value, "__await__"):
        return await value
    return value
