"""chat 调用与签名测试。"""

from __future__ import annotations

import argparse
import json

import pytest
from aiohttp import web

import anp_client
from anp_client import ClientError, build_chat_body, chat_service, format_rpc_error
from did_identity import load_or_create_identity
from signing import build_signed_headers


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
        (-32002, "请先运行 serve-did"),
        (-32001, "检查个人智能体 DID"),
        (-32003, "必须通过 chat 命令发送 DID WBA 签名请求"),
    ],
)
def test_format_rpc_error_guidance(code: int, expected: str) -> None:
    message = format_rpc_error({"code": code, "message": "错误"})
    assert expected in message


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
