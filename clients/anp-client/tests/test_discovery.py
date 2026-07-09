"""服务智能体发现测试。"""

from __future__ import annotations

import argparse
import json

import pytest
from aiohttp import web

import anp_client
from anp_client import (
    ClientError,
    discover_service,
    ensure_allowed_url,
    normalize_endpoint,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8900",
        "http://localhost:8900",
        "http://[::1]:8900",
        "https://example.com/agent/ad.json",
    ],
)
def test_ensure_allowed_url_accepts_safe_urls(url: str) -> None:
    ensure_allowed_url(url)


@pytest.mark.parametrize(
    "url", ["http://example.com", "http://192.168.1.10:8900", "ftp://127.0.0.1"]
)
def test_ensure_allowed_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ClientError, match="只允许 loopback HTTP 或 HTTPS"):
        ensure_allowed_url(url)


def test_normalize_endpoint_strips_trailing_slash() -> None:
    assert normalize_endpoint("http://127.0.0.1:8900/") == "http://127.0.0.1:8900"


@pytest.mark.asyncio
async def test_discover_service_from_endpoint(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "测试服务智能体",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "openrpc": "1.3.2",
                "methods": [{"name": "chat"}, {"name": "anp.get_capabilities"}],
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_service"
    assert service.name == "测试服务智能体"
    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"
    assert service.interface_url == f"{endpoint}/agent/interface.json"
    assert service.methods == ["chat", "anp.get_capabilities"]
    assert service.to_json() == {
        "service_did": "did:wba:localhost:agent:e1_service",
        "name": "测试服务智能体",
        "rpc_endpoint": f"{endpoint}/agent/rpc",
        "interface_url": f"{endpoint}/agent/interface.json",
        "methods": ["chat", "anp.get_capabilities"],
    }


@pytest.mark.asyncio
async def test_discover_rejects_non_anp_agent(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response({"protocolType": "OTHER"})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="目标不是 ANP 服务智能体"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_allows_missing_chat_for_discover(
    aiohttp_unused_port,
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "无 chat 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"openrpc": "1.3.2", "methods": [{"name": "anp.get_capabilities"}]}
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.methods == ["anp.get_capabilities"]


@pytest.mark.asyncio
async def test_discover_service_requires_chat_for_chat_calls(
    aiohttp_unused_port,
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "无 chat 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"openrpc": "1.3.2", "methods": [{"name": "anp.get_capabilities"}]}
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="服务智能体未声明 chat 方法"):
            await discover_service(endpoint=endpoint, ad_url=None, require_chat=True)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_from_ad_url_derives_rpc_endpoint(
    aiohttp_unused_port,
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    ad_url = f"{endpoint}/agent/ad.json"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "AD URL 服务",
                "did": "did:wba:localhost:agent:e1_adurl",
                "endpoint": endpoint,
                "interfaces": [
                    {
                        "type": "StructuredInterface",
                        "protocol": "openrpc",
                        "url": "/agent/interface.json",
                    }
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=None, ad_url=ad_url)
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_adurl"
    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"
    assert service.interface_url == f"{endpoint}/agent/interface.json"


@pytest.mark.asyncio
async def test_discover_service_selects_openrpc_interface_and_server_url(
    aiohttp_unused_port,
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    custom_rpc = f"{endpoint}/custom/rpc"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "自定义 RPC 服务",
                "did": "did:wba:localhost:agent:e1_custom",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "OtherInterface", "url": f"{endpoint}/wrong.json"},
                    {
                        "type": "StructuredInterface",
                        "protocol": "openrpc",
                        "url": f"{endpoint}/agent/interface.json",
                    },
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "openrpc": "1.3.2",
                "servers": [{"url": custom_rpc}],
                "methods": [{"name": "chat"}],
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.interface_url == f"{endpoint}/agent/interface.json"
    assert service.rpc_endpoint == custom_rpc


@pytest.mark.asyncio
async def test_discover_service_reports_http_failure(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    with pytest.raises(ClientError, match="无法连接服务智能体"):
        await discover_service(endpoint=endpoint, ad_url=None)


@pytest.mark.asyncio
async def test_discover_service_reports_non_2xx_status(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response({"error": "not found"}, status=404)

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="HTTP 404"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_reports_non_json_response(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.Response(text="not json", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="响应不是 JSON"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_reports_malformed_json_response(
    aiohttp_unused_port,
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.Response(text="{", content_type="application/json")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="响应不是 JSON"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_does_not_follow_redirects(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def redirect_handler(request: web.Request) -> web.Response:
        raise web.HTTPFound("http://example.com/agent/ad.json")

    app = web.Application()
    app.router.add_get("/agent/ad.json", redirect_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="不支持 HTTP redirect"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_does_not_create_identity_files(
    aiohttp_unused_port, client_home
) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "只读发现服务",
                "did": "did:wba:localhost:agent:e1_readonly",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert not (client_home / "did.json").exists()
    assert not (client_home / "private_key.pem").exists()


@pytest.mark.asyncio
async def test_cmd_discover_prints_human_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_discover_service(
        endpoint: str | None, ad_url: str | None, require_chat: bool = False
    ):
        assert endpoint == "http://127.0.0.1:8900"
        assert ad_url is None
        assert require_chat is False
        return anp_client.ServiceInfo(
            service_did="did:wba:localhost:agent:e1_cli",
            name="CLI 服务",
            rpc_endpoint="http://127.0.0.1:8900/agent/rpc",
            interface_url="http://127.0.0.1:8900/agent/interface.json",
            methods=["chat", "anp.get_capabilities"],
        )

    monkeypatch.setattr(anp_client, "discover_service", fake_discover_service)

    exit_code = await anp_client._cmd_discover(
        argparse.Namespace(endpoint="http://127.0.0.1:8900", ad_url=None, json=False)
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "服务智能体: CLI 服务" in output
    assert "服务 DID: did:wba:localhost:agent:e1_cli" in output
    assert "RPC endpoint: http://127.0.0.1:8900/agent/rpc" in output
    assert "OpenRPC interface: http://127.0.0.1:8900/agent/interface.json" in output
    assert "  - chat" in output
    assert "  - anp.get_capabilities" in output


@pytest.mark.asyncio
async def test_cmd_discover_prints_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_discover_service(
        endpoint: str | None, ad_url: str | None, require_chat: bool = False
    ):
        assert endpoint is None
        assert ad_url == "http://127.0.0.1:8900/agent/ad.json"
        assert require_chat is False
        return anp_client.ServiceInfo(
            service_did="did:wba:localhost:agent:e1_cli_json",
            name="JSON CLI 服务",
            rpc_endpoint="http://127.0.0.1:8900/agent/rpc",
            interface_url="http://127.0.0.1:8900/agent/interface.json",
            methods=["chat"],
        )

    monkeypatch.setattr(anp_client, "discover_service", fake_discover_service)

    exit_code = await anp_client._cmd_discover(
        argparse.Namespace(
            endpoint=None, ad_url="http://127.0.0.1:8900/agent/ad.json", json=True
        )
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "service_did": "did:wba:localhost:agent:e1_cli_json",
        "name": "JSON CLI 服务",
        "rpc_endpoint": "http://127.0.0.1:8900/agent/rpc",
        "interface_url": "http://127.0.0.1:8900/agent/interface.json",
        "methods": ["chat"],
    }
