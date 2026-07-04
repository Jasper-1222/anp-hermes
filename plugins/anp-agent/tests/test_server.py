"""ANP HTTP 端点服务器单元测试。"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import ANPAuth, AuthenticationError
from bridge import ANPBridge
from config import ANPConfig
from identity import ANPIdentity
from server import create_app


def _config(endpoint: str = "http://localhost:8900") -> ANPConfig:
    return ANPConfig(
        host="127.0.0.1",
        port=8900,
        hostname="localhost",
        endpoint=endpoint,
        data_dir=str(Path(__file__).parent / "data"),
        request_timeout=5,
        future_ttl=10,
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
    assert data["name"] == "Hermes ANP Agent"
    assert "description" in data
    assert data["endpoint"] == "http://localhost:8900"
    assert data["id"] == identity.did
    interfaces = data.get("interfaces", [])
    assert any(
        iface.get("type") == "StructuredInterface"
        and iface.get("protocol") == "openrpc"
        and "url" in iface
        for iface in interfaces
    )


@pytest.mark.asyncio
async def test_get_interface_json_contains_chat_method(client: TestClient):
    """GET /agent/interface.json 返回 OpenRPC 文档且包含 chat 方法。"""
    resp = await client.get("/agent/interface.json")
    assert resp.status == 200
    data = await resp.json()
    assert "openrpc" in data
    assert "methods" in data
    methods = [m["name"] for m in data["methods"]]
    assert "chat" in methods
    assert "components" in data
    assert "servers" in data


@pytest.mark.asyncio
async def test_post_rpc_success_returns_jsonrpc_response(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """合法 JSON-RPC 请求返回包含 result 的响应。"""
    mock_auth.authenticate = AsyncMock(return_value="did:wba:localhost:agent:caller")
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


@pytest.mark.asyncio
async def test_post_rpc_parse_error_returns_400_and_minus_32700(client: TestClient):
    """JSON 解析失败返回 HTTP 400 与 JSON-RPC -32700。"""
    resp = await client.post("/agent/rpc", data="not-json")
    assert resp.status == 400
    data = await resp.json()
    assert data["error"]["code"] == -32700
    assert "id" not in data or data.get("id") is None


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

    class FakeDidWbaVerifierError(Exception):
        pass

    exc = FakeDidWbaVerifierError("Failed to resolve DID document")
    auth_error = AuthenticationError("认证失败")
    auth_error.__cause__ = exc
    mock_auth.authenticate = AsyncMock(side_effect=auth_error)

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-4",
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
    mock_auth.authenticate = AsyncMock(return_value="did:wba:localhost:agent:caller")

    payload = {
        "jsonrpc": "2.0",
        "method": "unknown",
        "params": {},
        "id": "req-5",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_post_rpc_internal_error_returns_200_and_minus_32603(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """桥接层异常返回 HTTP 200 与 JSON-RPC -32603。"""
    mock_auth.authenticate = AsyncMock(return_value="did:wba:localhost:agent:caller")
    mock_bridge.call = AsyncMock(side_effect=RuntimeError("模拟内部错误"))

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-6",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 200
    data = await resp.json()
    assert data["error"]["code"] == -32603


@pytest.mark.asyncio
async def test_post_rpc_timeout_returns_200_and_minus_32603(
    client: TestClient,
    mock_auth: MagicMock,
    mock_bridge: MagicMock,
):
    """桥接层超时返回 HTTP 200 与 JSON-RPC -32603。"""
    mock_auth.authenticate = AsyncMock(return_value="did:wba:localhost:agent:caller")
    mock_bridge.call = AsyncMock(side_effect=asyncio.TimeoutError("模拟超时"))

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
