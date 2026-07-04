"""阶段一：确定性 Echo E2E 测试。"""

from __future__ import annotations

import json

import aiohttp
import pytest

from tests.helpers.signing import build_signed_headers


@pytest.mark.asyncio
async def test_echo_chat_returns_message(hermes_gateway, anp_caller_identity, did_document_server):
    """签名调用 chat 后应返回原消息。"""
    endpoint = hermes_gateway["endpoint"]
    target_url = f"{endpoint}/agent/rpc"
    message = "hello-e2e"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": message},
            "id": "echo-1",
        }
    )

    headers = await build_signed_headers(anp_caller_identity, target_url, body)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            target_url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "echo-1"
            assert "error" not in data
            assert message in data["result"]["response"]


@pytest.mark.asyncio
async def test_echo_ad_json_and_interface_json(hermes_gateway):
    """未受保护端点应正常返回。"""
    endpoint = hermes_gateway["endpoint"]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{endpoint}/agent/ad.json") as resp:
            assert resp.status == 200
            ad = await resp.json()
            assert ad["id"].startswith("did:wba:")
            assert ad["endpoint"] == endpoint

        async with session.get(f"{endpoint}/agent/interface.json") as resp:
            assert resp.status == 200
            iface = await resp.json()
            assert any(m["name"] == "chat" for m in iface["methods"])
