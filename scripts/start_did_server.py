#!/usr/bin/env python3
"""启动本地 DID 文档服务器，供 ANP 服务方解析调用方 DID。

用法:
    python3 start_did_server.py

默认监听 127.0.0.1:18900，可通过环境变量修改：
    export ANP_DID_SERVER_HOST=0.0.0.0
    export ANP_DID_SERVER_PORT=18900
    python3 start_did_server.py

启动后请保持终端运行，并在另一个终端启动 Hermes：
    export ANP_ALLOW_ALL_USERS=1
    export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
    hermes run
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

from aiohttp import web
from anp.authentication import create_did_wba_document

CALLER_DIR = Path.home() / ".anp-hermes-test-caller"

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


async def main() -> int:
    caller = _load_or_create_caller_identity()
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

    print(f"调用方 DID: {did}")
    print(f"DID 文档服务器: {base_url}")
    print(f"DID 文档 URL: {base_url}{route_path}")
    print("\n请在另一个终端启动 Hermes：")
    print("  export ANP_ALLOW_ALL_USERS=1")
    print(f"  export ANP_DID_RESOLVER_BASE_URL={base_url}")
    print("  hermes run")
    print("\n按 Ctrl+C 停止服务器。")

    stop_event = asyncio.Event()

    def _shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, _shutdown)

    await stop_event.wait()
    await runner.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
