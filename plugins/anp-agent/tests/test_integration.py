"""ANP 插件集成测试。

使用真实 ANP SDK 客户端签名，验证服务端 DID WBA 认证与 JSON-RPC 调用。
通过本地 DID 文档服务器绕过 verifier 默认 HTTPS 解析。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer, unused_port

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anp.authentication import DIDWbaAuthHeader, create_did_wba_document
from anp.authentication import did_wba_verifier as did_wba_verifier_module
from anp.authentication.did_resolver import resolve_did_document
from anp.authentication.did_wba import resolve_did_wba_document

from auth import create_auth
from bridge import ANPBridge, MessageEvent
from config import ANPConfig
from identity import load_or_create_identity
from server import create_app
from tests.helpers.did_server import DIDDocumentServer


def _config(endpoint: str, tmp_path: Path) -> ANPConfig:
    """构造测试用的 ANPConfig。"""
    return ANPConfig(
        host="127.0.0.1",
        port=0,
        hostname="localhost",
        endpoint=endpoint,
        data_dir=str(tmp_path / "anp-agent-data"),
        request_timeout=5,
        future_ttl=10,
    )


@pytest.fixture
def server_identity(tmp_path: Path):
    """生成临时服务端 DID WBA 身份。"""
    data_dir = tmp_path / "server"
    data_dir.mkdir(parents=True, exist_ok=True)
    return load_or_create_identity(data_dir, "localhost")


@pytest.fixture
def caller_identity(tmp_path: Path):
    """生成临时调用方 DID WBA 身份及文件路径。"""
    workdir = tmp_path / "caller"
    workdir.mkdir(parents=True, exist_ok=True)

    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    did = did_document["id"]
    auth_key = keys.get("key-1")
    assert auth_key is not None, "DID 文档未生成 key-1 认证密钥"
    private_key_pem = auth_key[0]

    did_path = workdir / "did.json"
    key_path = workdir / "private_key.pem"
    did_path.write_text(json.dumps(did_document), encoding="utf-8")
    key_path.write_bytes(private_key_pem)

    return {
        "did": did,
        "did_document": did_document,
        "private_key_pem": private_key_pem,
        "did_path": did_path,
        "key_path": key_path,
    }


@pytest_asyncio.fixture
async def did_server(caller_identity: dict[str, Any]) -> DIDDocumentServer:
    """启动本地 DID 文档服务器。"""
    async with DIDDocumentServer(caller_identity["did_document"]) as server:
        yield server


@pytest_asyncio.fixture
async def anp_app(
    tmp_path: Path,
    server_identity,
    did_server: DIDDocumentServer,
):
    """构造带 patched resolver 的插件应用与测试客户端。"""
    original_resolver = resolve_did_wba_document

    async def _patched_resolver(did: str, verify_proof: bool = False):
        return await resolve_did_document(
            did,
            base_url_override=did_server.base_url,
            verify_proof=verify_proof,
        )

    did_wba_verifier_module.resolve_did_wba_document = _patched_resolver

    try:
        # 先申请一个空闲端口，创建 config 时即使用实际端口，
        # 避免启动应用后再修改其状态（aiohttp 已弃用）。
        actual_port = unused_port()
        actual_endpoint = f"http://127.0.0.1:{actual_port}"
        config = _config(actual_endpoint, tmp_path)

        auth = create_auth(server_identity)

        handled = {}

        def message_handler(event: MessageEvent) -> None:
            """模拟 Hermes 核心：记录事件并异步设置结果。"""
            handled["event"] = event
            # 模拟异步处理：延迟一帧后回复
            asyncio.get_running_loop().call_later(
                0.05,
                lambda: bridge.set_result(event.message_id, f"收到: {event.text}"),
            )

        bridge = ANPBridge(config, message_handler)
        app = create_app(config, server_identity, auth, bridge)

        server = TestServer(app, host="127.0.0.1", port=actual_port)
        client = TestClient(server)
        await client.start_server()

        yield {
            "client": client,
            "endpoint": actual_endpoint,
            "bridge": bridge,
            "handled": handled,
        }

        await client.close()
        await bridge.stop()
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver


async def _build_signed_headers(
    caller_identity: dict[str, Any],
    target_url: str,
    body: str,
) -> dict[str, str]:
    """使用 DIDWbaAuthHeader 生成合法签名头。"""
    auth = DIDWbaAuthHeader(
        did_document_path=str(caller_identity["did_path"]),
        private_key_path=str(caller_identity["key_path"]),
        auth_mode="http_signatures",
    )
    headers = auth.get_auth_header(
        server_url=target_url,
        force_new=True,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=body,
    )
    headers["Content-Type"] = "application/json"
    return headers


@pytest.mark.asyncio
async def test_rpc_with_valid_signature_returns_result(anp_app, caller_identity):
    """合法签名请求应返回 JSON-RPC result。"""
    endpoint = anp_app["endpoint"]
    client: TestClient = anp_app["client"]
    handled = anp_app["handled"]

    target_url = f"{endpoint}/agent/rpc"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": "你好"},
            "id": "integ-1",
        }
    )
    headers = await _build_signed_headers(caller_identity, target_url, body)

    resp = await client.post("/agent/rpc", data=body, headers=headers)

    assert resp.status == 200
    data = await resp.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "integ-1"
    assert data["result"]["response"] == "收到: 你好"

    event = handled.get("event")
    assert event is not None
    assert event.metadata["anp_caller_did"] == caller_identity["did"]


@pytest.mark.asyncio
async def test_rpc_with_invalid_signature_returns_401(anp_app, caller_identity):
    """签名被篡改后应返回 HTTP 401。"""
    endpoint = anp_app["endpoint"]
    client: TestClient = anp_app["client"]

    target_url = f"{endpoint}/agent/rpc"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": "你好"},
            "id": "integ-2",
        }
    )
    headers = await _build_signed_headers(caller_identity, target_url, body)
    # 用固定无效字符串替换整个 Signature，避免假设原字符串长度
    headers["Signature"] = "sig1=:invalid_signature:"

    resp = await client.post("/agent/rpc", data=body, headers=headers)

    assert resp.status == 401
    data = await resp.json()
    assert "error" in data
    assert data["error"]["code"] == -32001


@pytest.mark.asyncio
async def test_rpc_without_signature_returns_401(anp_app):
    """缺少签名头应返回 HTTP 401。"""
    client: TestClient = anp_app["client"]

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": "你好"},
            "id": "integ-3",
        }
    )

    resp = await client.post(
        "/agent/rpc", data=body, headers={"Content-Type": "application/json"}
    )

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32001


@pytest.mark.asyncio
async def test_get_ad_json_and_interface_json(anp_app, server_identity):
    """未受保护的两个 JSON 端点应正常返回。"""
    client: TestClient = anp_app["client"]

    ad_resp = await client.get("/agent/ad.json")
    assert ad_resp.status == 200
    ad = await ad_resp.json()
    assert ad["id"] == server_identity.did
    assert ad["endpoint"] == anp_app["endpoint"]

    iface_resp = await client.get("/agent/interface.json")
    assert iface_resp.status == 200
    iface = await iface_resp.json()
    assert any(m["name"] == "chat" for m in iface["methods"])
