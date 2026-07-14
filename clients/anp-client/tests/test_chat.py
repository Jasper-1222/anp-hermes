"""chat 调用与签名测试。"""

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
from anp_client import ClientError, build_chat_body, chat_service, format_rpc_error
from did_identity import load_or_create_identity
from signing import build_signed_headers

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


@pytest.mark.asyncio
async def test_build_signed_headers_adds_content_type(client_home) -> None:
    identity = load_or_create_identity(client_home)
    body = json.dumps(
        {"jsonrpc": "2.0", "method": "chat", "params": {"message": "你好"}, "id": "1"}
    )

    headers = await build_signed_headers(
        identity, "http://127.0.0.1:8900/agent/rpc", body
    )

    assert headers["Content-Type"] == "application/json"
    assert "Signature" in headers
    assert "Signature-Input" in headers


def test_build_chat_body_uses_legacy_params_message() -> None:
    body, request_id = build_chat_body("你好", request_id="chat-test")
    data = json.loads(body)

    assert request_id == "chat-test"
    assert data == {
        "jsonrpc": "2.0",
        "id": "chat-test",
        "method": "chat",
        "params": {"message": "你好"},
    }


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (-32002, "Hermes gateway 启动前"),
        (-32001, "检查个人智能体 DID"),
        (-32003, "必须通过 chat 命令发送 DID WBA 签名请求"),
    ],
)
def test_format_rpc_error_guidance(code: int, expected: str) -> None:
    message = format_rpc_error({"code": code, "message": "错误"})
    assert expected in message


def test_format_rpc_error_did_resolver_guidance_names_hermes_gateway() -> None:
    message = format_rpc_error({"code": -32002, "message": "DID 文档无法解析"})

    assert "Hermes gateway 启动前" in message
    assert "ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900" in message
    assert "ANP_ALLOW_ALL_USERS=1" in message
    assert "重启 Hermes gateway" in message


def test_local_response_guidance_detects_pairing_code() -> None:
    text = "Hi~ I don't recognize you yet! Pairing code: G8T97879"

    guidance = anp_client.local_response_guidance(text)

    assert "ANP_ALLOW_ALL_USERS=1" in guidance
    assert "hermes pairing approve anp G8T97879" in guidance


def test_local_response_guidance_detects_sethome_prompt() -> None:
    text = "No home channel is set for Anp. Type /sethome to make this chat your home channel."

    guidance = anp_client.local_response_guidance(text)

    assert "发送 /sethome" in guidance
    assert "只需执行一次" in guidance


@pytest.mark.asyncio
async def test_chat_service_returns_json_result(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""
    captured_headers: dict[str, str] = {}

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "Echo 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        captured_headers.update(dict(request.headers))
        body = await request.json()
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"response": f"收到: {body['params']['message']}"},
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        result = await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()

    assert "Signature" in captured_headers
    assert "Signature-Input" in captured_headers
    assert result["service_did"] == "did:wba:localhost:agent:e1_service"
    assert result["caller_did"].startswith("did:wba:")
    assert result["http_status"] == 200
    assert result["response"] == "收到: hello"


@pytest.mark.asyncio
async def test_chat_service_reports_json_rpc_error(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "认证失败服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": "x",
                "error": {"code": -32002, "message": "DID 文档无法解析"},
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="请先运行 serve-did"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_uses_json_rpc_error_from_http_401(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "认证失败服务",
                "did": "did:wba:localhost:agent:e1_http_401",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        body = await request.json()
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": body["id"],
                "error": {"code": -32002, "message": "DID 文档无法解析"},
            },
            status=401,
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError) as excinfo:
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()

    assert excinfo.value.exit_code == 1
    assert "请先运行 serve-did" in str(excinfo.value)
    assert "HTTP 401" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_chat_service_rejects_mismatched_json_rpc_id(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "错配 id 服务",
                "did": "did:wba:localhost:agent:e1_bad_id",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": "other-id",
                "result": {"response": "不应接受"},
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="JSON-RPC 响应 id 不匹配"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_rejects_invalid_json_rpc_version(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "错版 JSON-RPC 服务",
                "did": "did:wba:localhost:agent:e1_bad_jsonrpc",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        body = await request.json()
        return web.json_response(
            {
                "jsonrpc": "1.0",
                "id": body["id"],
                "result": {"response": "不应接受"},
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="JSON-RPC 响应 jsonrpc 必须是 2.0"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_reports_http_failure(client_home) -> None:
    load_or_create_identity(client_home)

    with pytest.raises(ClientError, match="无法连接服务智能体"):
        await chat_service(endpoint="http://127.0.0.1:1", ad_url=None, message="hello")


@pytest.mark.asyncio
async def test_chat_service_requires_declared_chat_method(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "无 chat 服务",
                "did": "did:wba:localhost:agent:e1_no_chat",
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
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_reports_rpc_http_status(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "HTTP 错误服务",
                "did": "did:wba:localhost:agent:e1_http_error",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        return web.Response(status=500, text="boom", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="HTTP 500"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_reports_rpc_non_json(client_home) -> None:
    load_or_create_identity(client_home)
    endpoint = ""

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "非 JSON 服务",
                "did": "did:wba:localhost:agent:e1_non_json",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        return web.Response(text="not json", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner, endpoint = await _start_app(app)
    try:
        with pytest.raises(ClientError, match="响应不是 JSON"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


def test_main_chat_reports_client_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_chat_service(endpoint: str | None, ad_url: str | None, message: str):
        raise ClientError("清晰错误", exit_code=1)

    monkeypatch.setattr(anp_client, "chat_service", fake_chat_service)
    monkeypatch.setattr(
        "sys.argv",
        [
            "anp_client.py",
            "chat",
            "--endpoint",
            "http://127.0.0.1:8900",
            "--message",
            "你好",
        ],
    )

    exit_code = anp_client.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "清晰错误" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.asyncio
async def test_cmd_chat_prints_human_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_chat_service(endpoint: str | None, ad_url: str | None, message: str):
        assert endpoint == "http://127.0.0.1:8900"
        assert ad_url is None
        assert message == "你好"
        return {
            "service_did": "did:wba:localhost:agent:e1_cli",
            "caller_did": "did:wba:localhost:agent:e1_caller",
            "http_status": 200,
            "jsonrpc_id": "chat-test",
            "response": "收到: 你好",
        }

    monkeypatch.setattr(anp_client, "chat_service", fake_chat_service)

    exit_code = await anp_client._cmd_chat(
        argparse.Namespace(
            endpoint="http://127.0.0.1:8900", ad_url=None, message="你好", json=False
        )
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "服务 DID: did:wba:localhost:agent:e1_cli" in output
    assert "个人智能体 DID: did:wba:localhost:agent:e1_caller" in output
    assert "回复:" in output
    assert "收到: 你好" in output


@pytest.mark.asyncio
async def test_cmd_chat_prints_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_chat_service(endpoint: str | None, ad_url: str | None, message: str):
        assert endpoint is None
        assert ad_url == "http://127.0.0.1:8900/agent/ad.json"
        assert message == "hello"
        return {
            "service_did": "did:wba:localhost:agent:e1_cli_json",
            "caller_did": "did:wba:localhost:agent:e1_caller",
            "http_status": 200,
            "jsonrpc_id": "chat-json",
            "response": "hello",
        }

    monkeypatch.setattr(anp_client, "chat_service", fake_chat_service)

    exit_code = await anp_client._cmd_chat(
        argparse.Namespace(
            endpoint=None,
            ad_url="http://127.0.0.1:8900/agent/ad.json",
            message="hello",
            json=True,
        )
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "service_did": "did:wba:localhost:agent:e1_cli_json",
        "caller_did": "did:wba:localhost:agent:e1_caller",
        "http_status": 200,
        "jsonrpc_id": "chat-json",
        "response": "hello",
    }


@pytest.mark.asyncio
async def test_chat_cli_json_output(aiohttp_unused_port, client_home: Path) -> None:
    load_or_create_identity(client_home)
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    captured_headers: dict[str, str] = {}

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "CLI Echo",
                "did": "did:wba:localhost:agent:e1_cli_echo",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        captured_headers.update(dict(request.headers))
        body = await request.json()
        return web.json_response(
            {"jsonrpc": "2.0", "id": body["id"], "result": {"response": "pong"}}
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))
        returncode, stdout, stderr = await run_cli_async(
            ["chat", "--endpoint", endpoint, "--message", "ping", "--json"],
            env=env,
        )
    finally:
        await runner.cleanup()

    assert returncode == 0, stderr
    assert "Signature" in captured_headers
    data = json.loads(stdout)
    assert data["service_did"] == "did:wba:localhost:agent:e1_cli_echo"
    assert data["response"] == "pong"
