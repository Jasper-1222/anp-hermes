"""个人智能体本地 DID 文档服务。"""

from __future__ import annotations

import asyncio
import signal
from ipaddress import ip_address

from aiohttp import web

from did_identity import CallerIdentity


def is_loopback_host(host: str) -> bool:
    """判断监听地址是否为 loopback。"""
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def did_document_route(did: str) -> str:
    """根据 did:wba path DID 生成 DID 文档路径。"""
    path_segments = did.split(":")[3:]
    return "/" + "/".join(path_segments) + "/did.json"


def format_url_host(host: str) -> str:
    """把监听地址格式化为可用于 URL 的 host。"""
    try:
        if ip_address(host).version == 6:
            return f"[{host}]"
    except ValueError:
        pass
    return host


async def serve_did_document(
    identity: CallerIdentity,
    host: str = "127.0.0.1",
    port: int = 18900,
) -> int:
    """启动本地 DID 文档服务，直到收到 SIGINT/SIGTERM。"""
    if not is_loopback_host(host):
        raise ValueError("serve-did 第一期仅支持 loopback 监听地址")

    route_path = did_document_route(identity.did)

    async def _handler(request: web.Request) -> web.Response:
        return web.json_response(identity.did_document)

    app = web.Application()
    app.router.add_get(route_path, _handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    addresses = runner.addresses
    if not addresses:
        await runner.cleanup()
        raise RuntimeError("DID 文档服务器未能绑定到端口")
    address = addresses[0]
    actual_host, actual_port = address[0], address[1]
    base_url = f"http://{format_url_host(str(actual_host))}:{actual_port}"

    print(f"个人智能体 DID: {identity.did}")
    print(f"DID 文档服务器: {base_url}")
    print(f"DID 文档 URL: {base_url}{route_path}")
    print("serve-did 仅用于本地开发、测试和 E2E。")
    print("生产部署应按 DID WBA HTTPS 规则托管个人智能体 DID 文档。")
    print("\n本地服务智能体可设置：")
    print(f"  export ANP_DID_RESOLVER_BASE_URL={base_url}")
    print("\n按 Ctrl+C 停止服务器。")

    stop_event = asyncio.Event()

    def _shutdown() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    await stop_event.wait()
    await runner.cleanup()
    return 0
