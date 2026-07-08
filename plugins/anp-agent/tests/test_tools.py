"""Hermes tool exposure 策略单元测试。"""

import asyncio

import pytest

from anp_agent.config import ToolRPCConfig
from anp_agent.tools import (
    HIGH_RISK_TOOL_DENYLIST,
    ToolDefinition,
    ToolExposurePolicy,
    ToolRPCDispatcher,
    ToolRPCError,
    ToolRPCInvalidParamsError,
    ToolRPCInvocationFailedError,
    ToolRPCMethodNotFoundError,
    ToolRPCResultTooLargeError,
    ToolRPCTimeoutError,
    rpc_method_for_tool,
    tool_name_from_rpc_method,
)


@pytest.fixture
def tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="safe_tool",
            toolset="readonly",
            schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            description="安全工具",
        ),
        ToolDefinition(
            name="blocked_tool",
            toolset="readonly",
            schema={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="terminal",
            toolset="terminal",
            schema={"type": "object", "properties": {}},
        ),
    ]


def test_rpc_method_mapping_round_trip() -> None:
    """Hermes tool name 应稳定映射为 hermes.tool.* RPC method。"""
    assert rpc_method_for_tool("safe_tool") == "hermes.tool.safe_tool"
    assert tool_name_from_rpc_method("hermes.tool.safe_tool") == "safe_tool"
    assert tool_name_from_rpc_method("chat") is None


def test_disabled_policy_exposes_no_tools(tools: list[ToolDefinition]) -> None:
    """tool RPC 默认关闭时不暴露任何工具。"""
    policy = ToolExposurePolicy(ToolRPCConfig())

    assert policy.exposed_tools(tools) == []
    with pytest.raises(ToolRPCMethodNotFoundError):
        policy.require_tool("did:wba:localhost:agent:caller", "safe_tool", tools)


def test_enabled_without_allowlist_exposes_no_tools(tools: list[ToolDefinition]) -> None:
    """只开启 enabled 但没有 allowlist 时不暴露工具。"""
    policy = ToolExposurePolicy(ToolRPCConfig(enabled=True))

    assert policy.exposed_tools(tools) == []


def test_denylist_overrides_allowlist(tools: list[ToolDefinition]) -> None:
    """denylist 优先级应高于 allowed_tools。"""
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool", "blocked_tool"),
            denied_tools=("blocked_tool",),
        )
    )

    assert [tool.name for tool in policy.exposed_tools(tools)] == ["safe_tool"]
    with pytest.raises(ToolRPCMethodNotFoundError):
        policy.require_tool("did:wba:localhost:agent:caller", "blocked_tool", tools)


def test_builtin_high_risk_denylist_blocks_dangerous_tools(
    tools: list[ToolDefinition],
) -> None:
    """内置高风险 denylist 应默认拒绝危险工具。"""
    assert "terminal" in HIGH_RISK_TOOL_DENYLIST
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("terminal",),
        )
    )

    assert policy.exposed_tools(tools) == []
    with pytest.raises(ToolRPCMethodNotFoundError):
        policy.require_tool("did:wba:localhost:agent:caller", "terminal", tools)


def test_allowed_toolset_exposes_matching_tools(tools: list[ToolDefinition]) -> None:
    """allowed_toolsets 应允许同 toolset 下未被 deny 的工具。"""
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_toolsets=("readonly",),
            denied_tools=("blocked_tool",),
        )
    )

    assert [tool.name for tool in policy.exposed_tools(tools)] == ["safe_tool"]


def test_unauthorized_did_is_not_allowed(tools: list[ToolDefinition]) -> None:
    """未在 caller allowlist 中的 DID 不得调用工具。"""
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:alice",),
            allowed_tools=("safe_tool",),
        )
    )

    with pytest.raises(ToolRPCMethodNotFoundError):
        policy.require_tool("did:wba:localhost:agent:bob", "safe_tool", tools)


def test_allowed_did_can_require_tool(tools: list[ToolDefinition]) -> None:
    """授权 DID 可获取 allowlisted 工具定义。"""
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
        )
    )

    tool = policy.require_tool("did:wba:localhost:agent:caller", "safe_tool", tools)

    assert tool.name == "safe_tool"


def test_require_tool_rejects_missing_tool(tools: list[ToolDefinition]) -> None:
    """不存在的工具按 method not found 处理。"""
    policy = ToolExposurePolicy(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("missing",),
        )
    )

    with pytest.raises(ToolRPCMethodNotFoundError):
        policy.require_tool("did:wba:localhost:agent:caller", "missing", tools)


def test_tool_rpc_error_base_class() -> None:
    """工具 RPC 错误应携带 JSON-RPC 错误码。"""
    err = ToolRPCError("bad params", rpc_code=-32602)

    assert err.message == "bad params"
    assert err.rpc_code == -32602


@pytest.mark.asyncio
async def test_dispatcher_validates_required_params(
    tools: list[ToolDefinition],
) -> None:
    """缺少必填参数时不得执行工具。"""
    calls = []

    async def _invoke(tool_name: str, params: dict, **kwargs):
        calls.append((tool_name, params, kwargs))
        return {"ok": True}

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
    )

    with pytest.raises(ToolRPCInvalidParamsError):
        await dispatcher.call_tool(
            caller_did="did:wba:localhost:agent:caller",
            rpc_id="req-1",
            request_id="anp-req-1",
            tool_name="safe_tool",
            params={},
        )

    assert calls == []


@pytest.mark.asyncio
async def test_dispatcher_invokes_allowed_tool_with_high_level_invoker(
    tools: list[ToolDefinition],
) -> None:
    """合法工具调用应走注入的高层 invoker，而不是策略层直接 dispatch。"""
    calls = []

    async def _invoke(tool_name: str, params: dict, **kwargs):
        calls.append((tool_name, params, kwargs))
        return {"reply": params["message"]}

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
    )

    result = await dispatcher.call_tool(
        caller_did="did:wba:localhost:agent:caller",
        rpc_id="req-2",
        request_id="anp-req-2",
        tool_name="safe_tool",
        params={"message": "hello"},
    )

    assert result == {
        "content": {"reply": "hello"},
        "tool": "safe_tool",
        "metadata": {"request_id": "anp-req-2"},
    }
    assert calls == [
        (
            "safe_tool",
            {"message": "hello"},
            {
                "caller_did": "did:wba:localhost:agent:caller",
                "rpc_id": "req-2",
                "request_id": "anp-req-2",
            },
        )
    ]


@pytest.mark.asyncio
async def test_dispatcher_maps_timeout(tools: list[ToolDefinition]) -> None:
    """工具执行超时应映射为结构化 timeout 错误。"""

    async def _invoke(tool_name: str, params: dict, **kwargs):
        await asyncio.sleep(1)
        return {"ok": True}

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
            timeout_seconds=0,
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
    )

    with pytest.raises(ToolRPCTimeoutError) as exc_info:
        await dispatcher.call_tool(
            caller_did="did:wba:localhost:agent:caller",
            rpc_id="req-3",
            request_id="anp-req-3",
            tool_name="safe_tool",
            params={"message": "hello"},
        )

    assert exc_info.value.rpc_code == -32603
    assert exc_info.value.data["anp_code"] == "anp.tool_timeout"


@pytest.mark.asyncio
async def test_dispatcher_rejects_large_result(tools: list[ToolDefinition]) -> None:
    """超过 max_result_bytes 的工具结果不得完整返回。"""

    async def _invoke(tool_name: str, params: dict, **kwargs):
        return "x" * 20

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
            max_result_bytes=10,
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
    )

    with pytest.raises(ToolRPCResultTooLargeError) as exc_info:
        await dispatcher.call_tool(
            caller_did="did:wba:localhost:agent:caller",
            rpc_id="req-4",
            request_id="anp-req-4",
            tool_name="safe_tool",
            params={"message": "hello"},
        )

    assert exc_info.value.rpc_code == -32603
    assert exc_info.value.data["anp_code"] == "anp.tool_result_too_large"


@pytest.mark.asyncio
async def test_dispatcher_maps_invocation_failure(tools: list[ToolDefinition]) -> None:
    """工具执行异常应映射为安全内部错误。"""

    async def _invoke(tool_name: str, params: dict, **kwargs):
        raise RuntimeError("secret path /tmp/internal")

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
    )

    with pytest.raises(ToolRPCInvocationFailedError) as exc_info:
        await dispatcher.call_tool(
            caller_did="did:wba:localhost:agent:caller",
            rpc_id="req-5",
            request_id="anp-req-5",
            tool_name="safe_tool",
            params={"message": "hello"},
        )

    assert exc_info.value.rpc_code == -32603
    assert exc_info.value.message == "工具执行失败"
    assert "/tmp/internal" not in str(exc_info.value)
    assert exc_info.value.data["anp_code"] == "anp.tool_failed"


@pytest.mark.asyncio
async def test_dispatcher_records_audit_without_params_or_result(
    tools: list[ToolDefinition],
) -> None:
    """审计记录不得默认包含完整 params 或 result。"""
    audit_events = []

    async def _invoke(tool_name: str, params: dict, **kwargs):
        return {"secret": params["message"]}

    dispatcher = ToolRPCDispatcher(
        ToolRPCConfig(
            enabled=True,
            allowed_dids=("did:wba:localhost:agent:caller",),
            allowed_tools=("safe_tool",),
        ),
        list_tools=lambda: tools,
        invoke_tool=_invoke,
        audit=audit_events.append,
    )

    await dispatcher.call_tool(
        caller_did="did:wba:localhost:agent:caller",
        rpc_id="req-6",
        request_id="anp-req-6",
        tool_name="safe_tool",
        params={"message": "do-not-log"},
    )

    assert audit_events
    event = audit_events[-1]
    assert event["caller_did"] == "did:wba:localhost:agent:caller"
    assert event["rpc_id"] == "req-6"
    assert event["request_id"] == "anp-req-6"
    assert event["tool"] == "safe_tool"
    assert event["status"] == "success"
    assert "duration_ms" in event
    assert "params" not in event
    assert "result" not in event
    assert "do-not-log" not in str(event)
