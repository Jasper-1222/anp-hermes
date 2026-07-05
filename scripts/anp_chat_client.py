#!/usr/bin/env python3
"""手动测试 ANP Hermes 插件的 JSON-RPC chat 接口。

用法:
    # 1. 先启动 DID 文档服务器
    python3 start_did_server.py

    # 2. 在另一个终端启动 Hermes（ANP_DID_RESOLVER_BASE_URL 指向 DID 服务器）
    export ANP_ALLOW_ALL_USERS=1
    export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
    hermes run

    # 3. 运行本脚本发送 chat 请求
    export ANP_ENDPOINT=http://localhost:8900
    python3 anp_chat_client.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from typing import Any

import aiohttp
from anp.authentication import DIDWbaAuthHeader

DEFAULT_ENDPOINT = "http://localhost:8900"
CALLER_DIR = Path.home() / ".anp-hermes-test-caller"


def _load_caller_identity() -> dict:
    """加载已存在的调用方 DID WBA 身份。"""
    did_path = CALLER_DIR / "did.json"
    key_path = CALLER_DIR / "private_key.pem"

    if not did_path.exists() or not key_path.exists():
        print(
            "未找到调用方身份，请先运行 start_did_server.py 生成身份：\n"
            "  python3 start_did_server.py",
            file=sys.stderr,
        )
        sys.exit(1)

    did_document = json.loads(did_path.read_text(encoding="utf-8"))
    return {
        "did": did_document["id"],
        "did_document": did_document,
        "did_path": did_path,
        "key_path": key_path,
    }


async def _build_signed_headers(
    caller: dict, target_url: str, body: str
) -> dict[str, str]:
    """生成 HTTP Message Signature 请求头。"""
    auth = DIDWbaAuthHeader(
        did_document_path=str(caller["did_path"]),
        private_key_path=str(caller["key_path"]),
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


async def _discover(endpoint: str) -> None:
    """打印 Agent Description 与 OpenRPC 接口文档。"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{endpoint}/agent/ad.json") as resp:
            print("=== /agent/ad.json ===")
            print(json.dumps(await resp.json(), indent=2, ensure_ascii=False))
        async with session.get(f"{endpoint}/agent/interface.json") as resp:
            print("\n=== /agent/interface.json ===")
            print(json.dumps(await resp.json(), indent=2, ensure_ascii=False))


async def _chat(endpoint: str, caller: dict, message: str) -> dict:
    """发送 chat 请求并返回 JSON-RPC 响应。"""
    target_url = f"{endpoint}/agent/rpc"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": message},
            "id": "1",
        },
        ensure_ascii=False,
    )
    headers = await _build_signed_headers(caller, target_url, body)

    async with aiohttp.ClientSession() as session:
        async with session.post(target_url, headers=headers, data=body) as resp:
            return {
                "status": resp.status,
                "body": await resp.json(),
            }


async def main() -> int:
    endpoint = os.environ.get("ANP_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")
    caller = _load_caller_identity()

    print(f"服务端 endpoint: {endpoint}")
    print(f"调用方 DID: {caller['did']}\n")

    await _discover(endpoint)

    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = input("\n请输入要发送的消息: ").strip()

    if not message:
        print("消息为空，退出。")
        return 1

    print(f"\n发送: {message}")
    result = await _chat(endpoint, caller, message)
    print(f"HTTP 状态: {result['status']}")
    _print_response(result["body"])
    return 0


def _print_response(body: Any) -> None:
    """友好地打印 JSON-RPC 响应。"""
    error = body.get("error")
    if error is not None:
        print("响应错误:")
        print(f"  code: {error.get('code')}")
        print(f"  message: {error.get('message')}")
        return

    result = body.get("result")
    if isinstance(result, dict) and "response" in result:
        response_text = result["response"]
        if isinstance(response_text, str):
            print("\nHermes 回复:\n")
            print(response_text)
            return

    print("响应:")
    print(json.dumps(body, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
