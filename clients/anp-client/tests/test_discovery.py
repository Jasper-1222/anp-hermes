"""服务智能体发现测试。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from aiohttp import web

import anp_client
from anp_client import (
    ClientError,
    discover_service,
    ensure_allowed_url,
    normalize_endpoint,
)

CLIENT_ROOT = Path(__file__).resolve().parents[1]
CLI = CLIENT_ROOT / "scripts" / "anp_client.py"


async def run_cli_async(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """在 async 测试中运行 CLI，避免阻塞 aiohttp mock server 的 event loop。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(CLI),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    return proc.returncode or 0, stdout.decode(), stderr.decode()


async def _start_app(app: web.Application) -> tuple[web.AppRunner, str]:
    """用系统分配端口启动测试 HTTP 服务。"""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    address = runner.addresses[0]
    port = address[1]
    return runner, f"http://127.0.0.1:{port}"


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
    "url",
    [
        "http://example.com",
        "http://192.168.1.10:8900",
        "ftp://127.0.0.1",
        "http://[::1/agent/ad.json",
        "https://",
        "https:///agent/ad.json",
        "http://user:pass@127.0.0.1:8900/agent/rpc",
        "https://user@example.com/agent/ad.json",
        "http://127.0.0.1:8900/agent/rpc#fragment",
        "https://example.com/agent/ad.json#fragment",
        "http://127.0.0.1:99999/agent/rpc",
    ],
)
def test_ensure_allowed_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ClientError, match="只允许 loopback HTTP 或 HTTPS"):
        ensure_allowed_url(url)


def test_canonicalize_allowed_url_preserves_valid_request_target() -> None:
    assert (
        anp_client.canonicalize_allowed_url("http://127.0.0.1:8900/agent/rpc?trace=1")
        == "http://127.0.0.1:8900/agent/rpc?trace=1"
    )


def test_normalize_endpoint_strips_trailing_slash() -> None:
    assert normalize_endpoint("http://127.0.0.1:8900/") == "http://127.0.0.1:8900"


def test_service_info_to_json_copies_methods() -> None:
    service = anp_client.ServiceInfo(
        service_did="did:wba:localhost:agent:e1_service",
        name="测试服务",
        rpc_endpoint="http://127.0.0.1:8900/agent/rpc",
        interface_url="http://127.0.0.1:8900/agent/interface.json",
        methods=["chat"],
    )

    data = service.to_json()
    data["methods"].append("anp.get_capabilities")

    assert service.methods == ["chat"]


@pytest.mark.asyncio
async def test_discover_service_from_endpoint() -> None:
    endpoint = ""

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
    runner, endpoint = await _start_app(app)
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
async def test_discover_service_fallback_rpc_uses_endpoint_base_path() -> None:
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "带 base path 服务",
                "did": "did:wba:localhost:agent:e1_base_path",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/anp/agent/ad.json", ad_handler)
    app.router.add_get("/anp/agent/interface.json", interface_handler)
    runner, origin = await _start_app(app)
    endpoint = f"{origin}/anp"
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"


@pytest.mark.asyncio
async def test_discover_service_rejects_non_wba_service_did() -> None:
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "错误 DID 服务",
                "did": "did:example:evil",
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
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="服务 DID 必须是 did:wba:"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_requires_ad_endpoint_field() -> None:
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "缺少 endpoint 服务",
                "did": "did:wba:localhost:agent:e1_missing_endpoint",
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
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="Agent Description 缺少 RPC endpoint"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_requires_openrpc_interface_reference() -> None:
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "缺少 interface 服务",
                "did": "did:wba:localhost:agent:e1_missing_interface",
                "endpoint": endpoint,
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(
            ClientError, match="Agent Description 缺少 OpenRPC interface"
        ):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_rejects_non_anp_agent() -> None:
    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response({"protocolType": "OTHER"})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="目标不是 ANP 服务智能体"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_allows_missing_chat_for_discover() -> None:
    endpoint = ""

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
    runner, endpoint = await _start_app(app)
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.methods == ["anp.get_capabilities"]


@pytest.mark.asyncio
async def test_discover_service_requires_chat_for_chat_calls() -> None:
    endpoint = ""

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
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="服务智能体未声明 chat 方法"):
            await discover_service(endpoint=endpoint, ad_url=None, require_chat=True)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_from_ad_url_derives_rpc_endpoint() -> None:
    endpoint = ""

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
    runner, endpoint = await _start_app(app)
    try:
        service = await discover_service(
            endpoint=None, ad_url=f"{endpoint}/agent/ad.json"
        )
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_adurl"
    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"
    assert service.interface_url == f"{endpoint}/agent/interface.json"


@pytest.mark.asyncio
async def test_discover_service_selects_openrpc_interface_and_server_url() -> None:
    endpoint = ""

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
                "servers": [{"url": f"{endpoint}/custom/rpc"}],
                "methods": [{"name": "chat"}],
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner, endpoint = await _start_app(app)
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.interface_url == f"{endpoint}/agent/interface.json"
    assert service.rpc_endpoint == f"{endpoint}/custom/rpc"


@pytest.mark.asyncio
async def test_discover_service_resolves_relative_server_url_from_interface_url() -> (
    None
):
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "相对 RPC 服务",
                "did": "did:wba:localhost:agent:e1_relative",
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
                "servers": [{"url": "rpc"}],
                "methods": [{"name": "chat"}],
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner, endpoint = await _start_app(app)
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"


@pytest.mark.asyncio
async def test_discover_service_reports_http_failure() -> None:
    with pytest.raises(ClientError, match="无法连接服务智能体"):
        await discover_service(endpoint="http://127.0.0.1:1", ad_url=None)


@pytest.mark.asyncio
async def test_discover_service_reports_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        await asyncio.sleep(1)
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "超时服务",
                "did": "did:wba:localhost:agent:e1_timeout",
                "endpoint": endpoint,
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner, endpoint = await _start_app(app)
    original_timeout = anp_client.aiohttp.ClientTimeout
    monkeypatch.setattr(
        anp_client.aiohttp,
        "ClientTimeout",
        lambda total: original_timeout(total=0.01),
    )
    try:
        with pytest.raises(ClientError, match="无法连接服务智能体"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_reports_non_2xx_status() -> None:
    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response({"error": "not found"}, status=404)

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="HTTP 404"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_reports_non_json_response() -> None:
    async def ad_handler(request: web.Request) -> web.Response:
        return web.Response(text="not json", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="响应不是 JSON"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_reports_malformed_json_response() -> None:
    async def ad_handler(request: web.Request) -> web.Response:
        return web.Response(text="{", content_type="application/json")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="响应不是 JSON"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_does_not_follow_redirects() -> None:
    async def redirect_handler(request: web.Request) -> web.Response:
        raise web.HTTPFound("http://example.com/agent/ad.json")

    app = web.Application()
    app.router.add_get("/agent/ad.json", redirect_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="不支持 HTTP redirect"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_does_not_create_identity_files(client_home) -> None:
    endpoint = ""

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
    runner, endpoint = await _start_app(app)
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


@pytest.mark.asyncio
async def test_discover_cli_json_output(aiohttp_unused_port, client_home: Path) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "CLI 服务",
                "did": "did:wba:localhost:agent:e1_cli",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))
        returncode, stdout, stderr = await run_cli_async(
            ["discover", "--endpoint", endpoint, "--json"],
            env=env,
        )
    finally:
        await runner.cleanup()

    assert returncode == 0, stderr
    data = json.loads(stdout)
    assert data["service_did"] == "did:wba:localhost:agent:e1_cli"
    assert data["name"] == "CLI 服务"
    assert data["rpc_endpoint"] == f"{endpoint}/agent/rpc"
    assert data["interface_url"] == f"{endpoint}/agent/interface.json"
    assert data["methods"] == ["chat"]
    assert not (client_home / "did.json").exists()
    assert not (client_home / "private_key.pem").exists()
