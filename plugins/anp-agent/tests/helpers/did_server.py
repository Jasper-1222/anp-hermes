"""本地 DID 文档服务器测试辅助工具。

为集成测试提供可在本地启动/停止的 DID 文档托管服务，
用于绕过 ANP SDK verifier 默认的 HTTPS 解析。
"""

from __future__ import annotations

from typing import Any

from aiohttp import web


class DIDDocumentServer:
    """托管单个 DID 文档的本地 aiohttp 服务器。"""

    def __init__(
        self,
        did_document: dict[str, Any],
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        """构造 DID 文档服务器。

        Args:
            did_document: 要托管的完整 DID 文档，必须包含 id 字段。
            host: 监听地址。
            port: 监听端口，0 表示由系统分配。
        """
        self._did_document = did_document
        self._host = host
        self._port = port
        self._runner: web.AppRunner | None = None
        self._base_url = ""

    @property
    def base_url(self) -> str:
        """返回服务器 base URL，需在 start 之后访问。"""
        return self._base_url

    @property
    def document_url(self) -> str:
        """返回托管的 DID 文档完整 URL，需在 start 之后访问。"""
        did = self._did_document["id"]
        path_segments = did.split(":")[3:]
        return f"{self._base_url}/{'/'.join(path_segments)}/did.json"

    async def _handler(self, request: web.Request) -> web.Response:
        """返回托管的 DID 文档。"""
        return web.json_response(self._did_document)

    async def start(self) -> str:
        """启动服务器并返回 base URL。"""
        did = self._did_document["id"]
        path_segments = did.split(":")[3:]
        route_path = "/" + "/".join(path_segments) + "/did.json"

        app = web.Application()
        app.router.add_get(route_path, self._handler)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()

        actual_port = self._port
        if actual_port == 0:
            # 使用 AppRunner.addresses 公开 API 获取动态端口
            addresses = self._runner.addresses
            if addresses:
                actual_port = addresses[0][1]
            else:
                raise RuntimeError("DID 文档服务器未能绑定到可用端口")

        self._base_url = f"http://{self._host}:{actual_port}"
        return self._base_url

    async def stop(self) -> None:
        """停止服务器。"""
        if self._runner is not None:
            await self._runner.cleanup()
            self._base_url = ""
            self._runner = None

    async def __aenter__(self) -> DIDDocumentServer:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
