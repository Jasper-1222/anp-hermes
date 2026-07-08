"""阶段二：真实 LLM E2E 测试。

本模块验证 Hermes 在真实 LLM provider 配置下的 ANP JSON-RPC 调用能力。
所有测试默认被标记为 slow，仅在同时传入 --run-e2e 与 --run-slow-e2e 时执行。
"""

from __future__ import annotations

import json

import aiohttp
import pytest

from tests.helpers.signing import build_signed_headers


async def _signed_chat(
    session: aiohttp.ClientSession,
    endpoint: str,
    anp_caller_identity: dict,
    rpc_id: str,
    message: str,
) -> dict:
    """构造并发送签名的 chat JSON-RPC 请求，返回响应 JSON。"""
    target_url = f"{endpoint}/agent/rpc"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": message},
            "id": rpc_id,
        }
    )
    headers = await build_signed_headers(anp_caller_identity, target_url, body)
    async with session.post(
        target_url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
    ) as resp:
        assert resp.status == 200, f"HTTP 状态码非 200: {resp.status}"
        data = await resp.json()
        assert data.get("jsonrpc") == "2.0"
        assert data.get("id") == rpc_id
        assert "error" not in data, f"响应包含 error: {data.get('error')}"
        assert "result" in data
        response = data["result"].get("response", "")
        assert isinstance(response, str) and response.strip(), "LLM 返回空响应"
        return data


@pytest.mark.asyncio
@pytest.mark.slow
async def test_llm_single_turn_chat(
    llm_hermes_gateway,
    anp_caller_identity,
    did_document_server,
):
    """单轮 chat 应返回非空、无 error 的有效响应。"""

    async with aiohttp.ClientSession() as session:
        data = await _signed_chat(
            session,
            llm_hermes_gateway["endpoint"],
            anp_caller_identity,
            rpc_id="llm-single-1",
            message="你好",
        )
        assert "result" in data
        assert isinstance(data["result"].get("response"), str)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_llm_multi_turn_chat(
    llm_hermes_gateway,
    anp_caller_identity,
    did_document_server,
):
    """同一 caller DID 的多轮对话应保留上下文。"""

    async with aiohttp.ClientSession() as session:
        await _signed_chat(
            session,
            llm_hermes_gateway["endpoint"],
            anp_caller_identity,
            rpc_id="llm-multi-1",
            message="我叫 Alice",
        )

        data = await _signed_chat(
            session,
            llm_hermes_gateway["endpoint"],
            anp_caller_identity,
            rpc_id="llm-multi-2",
            message="我叫什么名字？",
        )
        response = data["result"]["response"]
        assert (
            "alice" in response.lower() or "艾丽丝" in response
        ), f"多轮响应未识别姓名 Alice: {response}"
