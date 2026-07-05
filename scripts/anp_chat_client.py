#!/usr/bin/env python3
"""手动测试 ANP Hermes 插件的 JSON-RPC chat 接口。

用法:
    # 1. 启动 Hermes gateway（需配置 ANP_DID_RESOLVER_BASE_URL 指向本脚本启动的 DID 文档服务器）
    export ANP_ALLOW_ALL_USERS=1
    export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
    hermes run

    # 2. 运行测试脚本
    export ANP_ENDPOINT=http://localhost:8900
    python3 anp_chat_client.py

脚本会启动一个本地 DID 文档服务器（默认 127.0.0.1:18900），供服务方解析调用方 DID；
同时在 ~/.anp-hermes-test-caller/ 生成或复用 caller 身份，对 /agent/rpc 发送签名请求。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp
from aiohttp import web
from anp.authentication import DIDWbaAuthHeader, create_did_wba_document

DEFAULT_ENDPOINT = "http://localhost:8900"
CALLER_DIR = Path.home() / ".anp-hermes-test-caller"

# DID 文档服务器默认监听地址，需与 Hermes 启动时的 ANP_DID_RESOLVER_BASE_URL 一致
_DID_SERVER_HOST = os.environ.get("ANP_DID_SERVER_HOST", "127.0.0.1")
_DID_SERVER_PORT = int(os.environ.get("ANP_DID_SERVER_PORT", "18900"))


def _load_or_create_caller_identity() -> dict:
    """加载或创建测试调用方 DID WBA 身份。"""
    CALLER_DIR.mkdir(parents=True, exist_ok=True)
    did_path = CALLER_DIR / "did.json"
    key_path = CALLER_DIR / "private_key.pem"

    if did_path.exists() and key_path.exists():
        did_document = json.loads(did_path.read_text(encoding="utf-8"))
        return {
            "did": did_document["id"],
            "did_document": did_document,
            "did_path": did_path,
            "key_path": key_path,
        }

    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    private_key_pem = keys["key-1"][0]
    did_path.write_text(json.dumps(did_document, indent=2), encoding="utf-8")
    key_path.write_bytes(private_key_pem)

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


async def _start_did_document_server(caller: dict) -> tuple[str, web.AppRunner]:
    """启动本地 DID 文档服务器，返回 (base_url, runner)。"""
    did_document = caller["did_document"]
    did = caller["did"]
    path_segments = did.split(":")[3:]
    route_path = "/" + "/".join(path_segments) + "/did.json"

    async def _handler(request: web.Request) -> web.Response:
        return web.json_response(did_document)

    app = web.Application()
    app.router.add_get(route_path, _handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, _DID_SERVER_HOST, _DID_SERVER_PORT)
    await site.start()

    addresses = runner.addresses
    if not addresses:
        await runner.cleanup()
        raise RuntimeError("DID 文档服务器未能绑定到端口")
    actual_host, actual_port = addresses[0]
    base_url = f"http://{actual_host}:{actual_port}"
    return base_url, runner


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
    caller = _load_or_create_caller_identity()

    print(f"服务端 endpoint: {endpoint}")
    print(f"调用方 DID: {caller['did']}")

    did_url, did_runner = await _start_did_document_server(caller)
    print(f"DID 文档服务器: {did_url}")
    print(f"请确保 Hermes 已设置 ANP_DID_RESOLVER_BASE_URL={did_url}\n")

    try:
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
        print("响应:")
        print(json.dumps(result["body"], indent=2, ensure_ascii=False))
        return 0
    finally:
        await did_runner.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
