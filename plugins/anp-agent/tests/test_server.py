"""ANP HTTP 端点服务器单元测试。"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from anp_agent.auth import ANPAuth, AuthenticationError, AuthenticationResult
from anp_agent.bridge import ANPBridge, ANPBridgeError
from anp_agent.config import ANPConfig, ToolRPCConfig
from anp_agent.identity import ANPIdentity
from anp_agent.server import create_app
from anp_agent.tools import ToolDefinition


def _config(endpoint: str = "http://localhost:8900", **extra) -> ANPConfig:
    return ANPConfig(
        host="127.0.0.1",
        port=8900,
        hostname="localhost",
        endpoint=endpoint,
        data_dir=str(Path(__file__).parent / "data"),
        request_timeout=5,
        future_ttl=10,
        **extra,
    )


@pytest.fixture
def identity() -> ANPIdentity:
    return ANPIdentity(
        did="did:wba:localhost:agent:e1_test",
        did_document={"id": "did:wba:localhost:agent:e1_test"},
        private_key_pem=b"fake-key",
        data_dir=Path("/tmp/anp-test-server"),
    )


@pytest.fixture
def mock_auth() -> MagicMock:
    return MagicMock(spec=ANPAuth)


@pytest.fixture
def mock_bridge() -> MagicMock:
    return MagicMock(spec=ANPBridge)


@pytest_asyncio.fixture
async def client(
    identity: ANPIdentity,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
) -> TestClient:
    app = create_app(_config(), identity, mock_auth, mock_bridge)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def tool_client(
    identity: ANPIdentity,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
) -> TestClient:
    tool = ToolDefinition(
        name="safe_tool",
        toolset="readonly",
        schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        description="安全测试工具",
    )

    async def _invoke_tool(tool_name, params, **kwargs):
        if params.get("message") == "fail":
            raise RuntimeError("internal secret")
        return {"echo": params["message"]}

    app = create_app(
        _config(
            tool_rpc=ToolRPCConfig(
                enabled=True,
                allowed_dids=("did:wba:localhost:agent:caller",),
                allowed_tools=("safe_tool", "blocked_tool", "terminal"),
                denied_tools=("blocked_tool",),
            )
        ),
        identity,
        mock_auth,
        mock_bridge,
        list_tools=lambda: [
            tool,
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
        ],
        invoke_tool=_invoke_tool,
    )
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_get_did_json_returns_identity_document(
    identity: ANPIdentity,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """GET /agent/did.json 返回服务端 DID 文档。"""
    app = create_app(_config(), identity, mock_auth, mock_bridge)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        # DID 路径由 DID 的 path segments 决定：did:wba:localhost:agent:e1_test
        resp = await client.get("/agent/e1_test/did.json")
        assert resp.status == 200
        data = await resp.json()
        assert data["id"] == identity.did
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_ad_json_returns_required_fields(client: TestClient, identity: ANPIdentity):
    """GET /agent/ad.json 返回合法 JSON 且包含必要字段。"""
    resp = await client.get("/agent/ad.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["protocolType"] == "ANP"
    assert data["protocolVersion"] == "1.0.0"
    assert data["type"] == "AgentDescription"
    assert data["url"] == "http://localhost:8900/agent/ad.json"
    assert data["name"] == "Hermes ANP Agent"
    assert "description" in data
    assert data["endpoint"] == "http://localhost:8900"
    assert data["id"] == identity.did
    assert data["did"] == identity.did
    assert data["security"] == "didwba_sc"
    assert data["securityDefinitions"] == {
        "didwba_sc": {
            "scheme": "didwba",
            "in": "header",
            "name": "Authorization",
        }
    }
    interfaces = data.get("interfaces", [])
    assert any(
        iface.get("type") == "StructuredInterface"
        and iface.get("protocol") == "openrpc"
        and "url" in iface
        for iface in interfaces
    )
    ad_text = json.dumps(data, ensure_ascii=False).lower()
    for unsupported in ("direct", "group", "e2ee", "dtr", "portal", "mediator", "hermes tools"):
        assert unsupported not in ad_text


@pytest.mark.asyncio
async def test_get_well_known_agent_descriptions_returns_collection_page(
    client: TestClient,
):
    """GET /.well-known/agent-descriptions 返回 JSON-LD CollectionPage。"""
    resp = await client.get("/.well-known/agent-descriptions")

    assert resp.status == 200
    data = await resp.json()
    assert data["@context"] == {
        "@vocab": "https://schema.org/",
        "did": "https://w3id.org/did#",
        "ad": "https://agent-network-protocol.com/ad#",
    }
    assert data["@type"] == "CollectionPage"
    assert data["url"] == "http://localhost:8900/.well-known/agent-descriptions"
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_well_known_agent_descriptions_contains_current_agent_index(
    client: TestClient,
    identity: ANPIdentity,
):
    """CollectionPage 只包含当前服务智能体的轻量索引项。"""
    ad_resp = await client.get("/agent/ad.json")
    ad_data = await ad_resp.json()

    resp = await client.get("/.well-known/agent-descriptions")

    assert resp.status == 200
    data = await resp.json()
    assert data["items"] == [
        {
            "@type": "ad:AgentDescription",
            "name": ad_data["name"],
            "@id": "http://localhost:8900/agent/ad.json",
            "did": identity.did,
        }
    ]


@pytest.mark.asyncio
async def test_get_well_known_agent_descriptions_item_is_not_full_ad(
    client: TestClient,
):
    """CollectionPage item 引用 /agent/ad.json，不内嵌完整 AD。"""
    resp = await client.get("/.well-known/agent-descriptions")

    assert resp.status == 200
    item = (await resp.json())["items"][0]
    assert item["@id"] == "http://localhost:8900/agent/ad.json"
    assert "description" not in item
    assert "endpoint" not in item
    assert "interfaces" not in item


@pytest.mark.asyncio
async def test_get_well_known_agent_descriptions_does_not_authenticate(
    client: TestClient,
    mock_auth: MagicMock,
):
    """well-known 发现端点公开访问，不进入认证流程。"""
    resp = await client.get("/.well-known/agent-descriptions")

    assert resp.status == 200
    mock_auth.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_get_interface_json_contains_chat_method(client: TestClient):
    """GET /agent/interface.json 返回 OpenRPC 文档且包含当前方法。"""
    resp = await client.get("/agent/interface.json")
    assert resp.status == 200
    data = await resp.json()
    assert "openrpc" in data
    assert "methods" in data
    methods = {m["name"]: m for m in data["methods"]}
    assert "chat" in methods
    assert "anp.get_capabilities" in methods
    assert "params.body.message" in methods["chat"]["description"]
    assert "能力" in methods["anp.get_capabilities"]["summary"]
    assert "components" in data
    assert "servers" in data
    assert not any(name.startswith("hermes.tool.") for name in methods)


@pytest.mark.asyncio
async def test_get_interface_json_declares_allowlisted_tool_method(tool_client: TestClient):
    """tool RPC 启用时 OpenRPC 应声明 allowlisted 工具方法。"""
    resp = await tool_client.get("/agent/interface.json")

    assert resp.status == 200
    data = await resp.json()
    methods = {m["name"]: m for m in data["methods"]}
    assert "hermes.tool.safe_tool" in methods
    assert "hermes.tool.blocked_tool" not in methods
    assert "hermes.tool.terminal" not in methods
    params_schema = methods["hermes.tool.safe_tool"]["params"][0]["schema"]
    assert params_schema["required"] == ["message"]


@pytest.mark.asyncio
async def test_ad_json_declares_tools_only_when_enabled(tool_client: TestClient):
    """AD 只在存在 allowlisted tools 时声明 Hermes tools 能力。"""
    resp = await tool_client.get("/agent/ad.json")

    assert resp.status == 200
    data = await resp.json()
    assert "hermes_tools" in data["capabilities"]
    assert data["capabilities"]["hermes_tools"] == ["hermes.tool.safe_tool"]


@pytest.mark.asyncio
async def test_post_rpc_tool_method_returns_32601_when_disabled(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """tool RPC 关闭时 hermes.tool.* 返回 method not found。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "hermes.tool.safe_tool",
        "params": {"message": "hello"},
        "id": "req-tool-disabled",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32601
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_allowlisted_tool_success(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """allowlisted Hermes tool 应返回 JSON-RPC 成功响应。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "hermes.tool.safe_tool",
        "params": {"message": "hello"},
        "id": "req-tool-ok",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert resp.headers.get("Authentication-Info") == 'access_token="token"'
    data = await resp.json()
    assert data["result"]["tool"] == "safe_tool"
    assert data["result"]["content"] == {"echo": "hello"}
    assert data["result"]["metadata"]["request_id"] == "req-tool-ok"
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_tool_rejects_unauthorized_did(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """未授权 DID 调用 allowlisted tool 时应返回 -32601 且不泄露差异。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:bob",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "hermes.tool.safe_tool",
        "params": {"message": "hello"},
        "id": "req-tool-unauthorized",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32601
    assert "safe_tool" not in data["error"]["message"]
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["hermes.tool.blocked_tool", "hermes.tool.terminal"])
async def test_post_rpc_tool_rejects_denied_tools(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
    method: str,
):
    """denylisted 与内置高风险工具应返回 -32601。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": {},
        "id": "req-tool-denied",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == -32601
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_tool_invalid_params_returns_32602(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """tool params 无效时返回 -32602 且不附带认证成功头。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "hermes.tool.safe_tool",
        "params": {},
        "id": "req-tool-bad-params",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32602
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_tool_failure_returns_32603_without_auth_info(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """tool 执行失败时返回 -32603，且不附带成功认证头或内部异常。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "hermes.tool.safe_tool",
        "params": {"message": "fail"},
        "id": "req-tool-fail",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32603
    assert data["error"]["data"]["anp_code"] == "anp.tool_failed"
    assert "internal secret" not in data["error"]["message"]
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_success_returns_jsonrpc_response(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """合法 JSON-RPC 请求返回包含 result 的响应。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )
    mock_bridge.call = AsyncMock(return_value="你好，世界")

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-1",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "req-1"
    assert data["result"]["response"] == "你好，世界"

    mock_auth.authenticate.assert_awaited_once()
    mock_bridge.call.assert_awaited_once_with(
        "req-1", "chat", {"message": "你好"}, "did:wba:localhost:agent:caller"
    )
    assert "Authentication-Info" not in resp.headers


@pytest.mark.asyncio
async def test_post_rpc_success_forwards_authentication_info(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """合法 JSON-RPC 成功响应应转发 Authentication-Info 头。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )
    mock_bridge.call = AsyncMock(return_value="你好，世界")

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-auth-info",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert resp.headers.get("Authentication-Info") == 'access_token="token"'
    data = await resp.json()
    assert data["result"]["response"] == "你好，世界"


@pytest.mark.asyncio
async def test_post_rpc_core_binding_body_message_used_for_chat(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """Core Binding envelope 中的 params.body.message 应作为 chat 文本。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )
    mock_bridge.call = AsyncMock(return_value="你好，Core Binding")

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "meta": {
                "profile": "anp.core.binding.v1",
                "security_profile": "transport-protected",
            },
            "body": {"message": "来自 body"},
        },
        "id": "req-core-chat",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["response"] == "你好，Core Binding"
    mock_bridge.call.assert_awaited_once()
    _, _, params, _ = mock_bridge.call.await_args.args
    assert params["message"] == "来自 body"
    assert params["body"]["message"] == "来自 body"


@pytest.mark.asyncio
async def test_post_rpc_core_binding_body_message_precedes_legacy_message(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """同时存在 body.message 和 legacy message 时优先使用 body.message。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )
    mock_bridge.call = AsyncMock(return_value="优先 body")

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "message": "legacy message",
            "meta": {
                "profile": "anp.core.binding.v1",
                "security_profile": "transport-protected",
            },
            "body": {"message": "body message"},
        },
        "id": "req-body-first",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    _, _, params, _ = mock_bridge.call.await_args.args
    assert params["message"] == "body message"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"meta": [], "body": {}},
        {"meta": {"profile": "anp.core.binding.v1"}, "body": []},
    ],
)
async def test_post_rpc_invalid_core_binding_shape_returns_anp_error(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
    params,
):
    """无效 Core Binding envelope shape 返回 1003 与 anp.invalid_params_shape。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {"jsonrpc": "2.0", "method": "chat", "params": params, "id": "req-shape"}
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == 1003
    assert data["error"]["data"]["anp_code"] == "anp.invalid_params_shape"
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_unsupported_profile_returns_anp_error(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """不支持的 profile 返回 1001 与 anp.unsupported_profile。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "meta": {
                "profile": "anp.direct.base.v1",
                "security_profile": "transport-protected",
            },
            "body": {"message": "hi"},
        },
        "id": "req-unsupported-profile",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == 1001
    assert data["error"]["data"]["anp_code"] == "anp.unsupported_profile"
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_unsupported_security_profile_returns_anp_error(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """不支持的 security_profile 返回 1002 与 anp.unsupported_security_profile。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {
            "meta": {
                "profile": "anp.core.binding.v1",
                "security_profile": "direct-e2ee",
            },
            "body": {"message": "hi"},
        },
        "id": "req-unsupported-security",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == 1002
    assert data["error"]["data"]["anp_code"] == "anp.unsupported_security_profile"
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_get_capabilities_returns_runtime_capabilities(
    client: TestClient,
    identity: ANPIdentity,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """anp.get_capabilities 返回当前运行时能力且不调用 bridge。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "anp.get_capabilities",
        "params": {
            "meta": {
                "profile": "anp.core.binding.v1",
                "security_profile": "transport-protected",
            },
            "body": {},
        },
        "id": "req-capabilities",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert resp.headers.get("Authentication-Info") == 'access_token="token"'
    data = await resp.json()
    result = data["result"]
    assert result["service_did"] == identity.did
    assert result["supported_profiles"] == ["anp.core.binding.v1"]
    assert result["supported_security_profiles"] == ["transport-protected"]
    assert result["limits"]["max_request_bytes"] == str(1024 * 1024)
    assert "text/plain" in result["supported_content_types"]
    assert "application/json" in result["supported_content_types"]
    assert "hermes_tools" not in result
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_get_capabilities_declares_enabled_tool_methods(
    tool_client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """capabilities 应在 tool RPC 启用时声明当前工具方法。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "anp.get_capabilities",
        "params": {},
        "id": "req-tool-capabilities",
    }
    resp = await tool_client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["hermes_tools"] == ["hermes.tool.safe_tool"]
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_get_capabilities_accepts_legacy_empty_params(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """anp.get_capabilities 可接受空 params，保持当前 RPC 入口兼容。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "anp.get_capabilities",
        "params": {},
        "id": "req-capabilities-legacy",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["supported_profiles"] == ["anp.core.binding.v1"]
    mock_bridge.call.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_parse_error_returns_400_and_minus_32700(client: TestClient):
    """JSON 解析失败返回 HTTP 400 与 JSON-RPC -32700。"""
    resp = await client.post("/agent/rpc", data="not-json")
    assert resp.status == 400
    data = await resp.json()
    assert data["error"]["code"] == -32700
    assert "id" not in data or data.get("id") is None


@pytest.mark.asyncio
async def test_post_rpc_invalid_jsonrpc_version_returns_400_and_minus_32600(
    client: TestClient,
    mock_auth: MagicMock,
):
    """无效 jsonrpc 版本返回 HTTP 400 与 JSON-RPC -32600。"""
    payload = {"jsonrpc": "1.0", "method": "chat", "params": {}, "id": "req-bad-version"}
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 400
    data = await resp.json()
    assert data["id"] == "req-bad-version"
    assert data["error"]["code"] == -32600
    mock_auth.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_batch_returns_400_and_minus_32600_without_auth(
    client: TestClient,
    mock_auth: MagicMock,
):
    """batch 请求返回 HTTP 400 与 JSON-RPC -32600，且不进入认证。"""
    payload = [{"jsonrpc": "2.0", "method": "chat", "params": {}, "id": "req-batch"}]
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 400
    data = await resp.json()
    assert data["id"] is None
    assert data["error"]["code"] == -32600
    mock_auth.authenticate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rpc_id",
    [None, "", 1],
)
async def test_post_rpc_invalid_id_returns_400_and_minus_32600(
    client: TestClient,
    mock_auth: MagicMock,
    rpc_id,
):
    """缺少、空字符串或数字 id 返回 HTTP 400 与 JSON-RPC -32600。"""
    payload = {"jsonrpc": "2.0", "method": "chat", "params": {}}
    if rpc_id is not None:
        payload["id"] = rpc_id

    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 400
    data = await resp.json()
    assert data["id"] is None
    assert data["error"]["code"] == -32600
    mock_auth.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_missing_method_returns_400_and_minus_32600(
    client: TestClient,
):
    """缺少 method 返回 HTTP 400 与 JSON-RPC -32600。"""
    payload = {"jsonrpc": "2.0", "params": {}, "id": "req-2"}
    resp = await client.post("/agent/rpc", data=json.dumps(payload))
    assert resp.status == 400
    data = await resp.json()
    assert data["error"]["code"] == -32600


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"jsonrpc": "2.0", "method": 123, "params": {}, "id": "req-bad-method"},
        {"jsonrpc": "2.0", "method": "chat", "params": [], "id": "req-bad-params"},
    ],
)
async def test_post_rpc_invalid_method_or_params_returns_400_and_minus_32600(
    client: TestClient,
    mock_auth: MagicMock,
    payload,
):
    """非字符串 method 或非对象 params 返回 HTTP 400 与 JSON-RPC -32600。"""
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 400
    data = await resp.json()
    assert data["id"] == payload["id"]
    assert data["error"]["code"] == -32600
    mock_auth.authenticate.assert_not_called()


@pytest.mark.asyncio
async def test_post_rpc_auth_failure_returns_401_and_minus_32001(
    client: TestClient,
    mock_auth: MagicMock,
):
    """认证失败返回 HTTP 401 与 JSON-RPC -32001。"""
    mock_auth.authenticate = AsyncMock(side_effect=AuthenticationError("认证失败"))

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-3",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32001


@pytest.mark.asyncio
async def test_post_rpc_unresolvable_did_returns_401_and_minus_32002(
    client: TestClient,
    mock_auth: MagicMock,
):
    """DID 无法解析返回 HTTP 401 与 JSON-RPC -32002。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID 文档无法解析",
            status_code=401,
            rpc_code=-32002,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-unresolvable",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32002


@pytest.mark.asyncio
async def test_post_rpc_method_not_found_returns_200_and_minus_32601(
    client: TestClient,
    mock_auth: MagicMock,
):
    """方法不存在返回 HTTP 200 与 JSON-RPC -32601。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "unknown",
        "params": {},
        "id": "req-5",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_post_rpc_internal_error_returns_200_and_minus_32603(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """桥接层异常返回 HTTP 200 与 JSON-RPC -32603。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult(
            "did:wba:localhost:agent:caller",
            {"Authentication-Info": 'access_token="token"'},
        )
    )
    mock_bridge.call = AsyncMock(side_effect=ANPBridgeError("模拟内部错误"))

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-6",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    assert "Authentication-Info" not in resp.headers
    data = await resp.json()
    assert data["error"]["code"] == -32603


@pytest.mark.asyncio
async def test_post_rpc_timeout_returns_200_and_minus_32603(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """桥接层超时返回 HTTP 200 与 JSON-RPC -32603。"""
    mock_auth.authenticate = AsyncMock(
        return_value=AuthenticationResult("did:wba:localhost:agent:caller", {})
    )
    mock_bridge.call = AsyncMock(side_effect=ANPBridgeError("模拟超时"))

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-7",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == -32603


@pytest.mark.asyncio
async def test_post_rpc_missing_auth_returns_401_and_minus_32003(
    client: TestClient,
    mock_auth: MagicMock,
):
    """缺少认证头返回 HTTP 401 与 JSON-RPC -32003。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "缺少认证头",
            status_code=401,
            rpc_code=-32003,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-missing-auth",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32003
    assert data["error"]["message"] == "缺少认证头"


@pytest.mark.asyncio
async def test_post_rpc_invalid_did_document_returns_401_and_minus_32004(
    client: TestClient,
    mock_auth: MagicMock,
):
    """DID 文档无效返回 HTTP 401 与 JSON-RPC -32004。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID 文档无效",
            status_code=401,
            rpc_code=-32004,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-invalid-did",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32004


@pytest.mark.asyncio
async def test_post_rpc_unauthorized_verification_method_returns_403_and_minus_32005(
    client: TestClient,
    mock_auth: MagicMock,
):
    """认证方法未授权返回 HTTP 403 与 JSON-RPC -32005。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "认证方法未授权",
            status_code=403,
            rpc_code=-32005,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-unauthorized-vm",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 403
    data = await resp.json()
    assert data["error"]["code"] == -32005


@pytest.mark.asyncio
async def test_post_rpc_internal_auth_error_returns_500_and_minus_32006(
    client: TestClient,
    mock_auth: MagicMock,
):
    """认证内部错误返回 HTTP 500 与 JSON-RPC -32006。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "认证服务内部错误",
            status_code=500,
            rpc_code=-32006,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-internal",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 500
    data = await resp.json()
    assert data["error"]["code"] == -32006


@pytest.mark.asyncio
async def test_post_rpc_challenge_headers_forwarded(
    client: TestClient,
    mock_auth: MagicMock,
):
    """401 响应应转发 WWW-Authenticate 与 Accept-Signature 头。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID WBA 签名无效",
            status_code=401,
            rpc_code=-32001,
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"',
                "Accept-Signature": 'sig1=("@method")',
                "X-Internal": "should-not-forward",
            },
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-challenge",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    assert resp.headers.get("WWW-Authenticate") == 'Bearer error="invalid_token"'
    assert resp.headers.get("Accept-Signature") == 'sig1=("@method")'
    assert "X-Internal" not in resp.headers
