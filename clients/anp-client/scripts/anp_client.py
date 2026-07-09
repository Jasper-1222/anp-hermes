#!/usr/bin/env python3
"""通用 ANP client skill 命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import aiohttp

from did_identity import IdentityError, load_or_create_identity
from did_server import is_loopback_host, serve_did_document
from signing import build_signed_headers


class ClientError(RuntimeError):
    """anp-client 可展示给用户的错误。"""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class ServiceInfo:
    """已发现的 ANP 服务智能体信息。"""

    service_did: str
    name: str
    rpc_endpoint: str
    interface_url: str
    methods: list[str]

    def to_json(self) -> dict[str, Any]:
        """返回适合 CLI JSON 输出的结构。"""
        return {
            "service_did": self.service_did,
            "name": self.name,
            "rpc_endpoint": self.rpc_endpoint,
            "interface_url": self.interface_url,
            "methods": list(self.methods),
        }


def normalize_endpoint(endpoint: str) -> str:
    """规范化 endpoint。"""
    return endpoint.rstrip("/")


def ensure_allowed_url(url: str) -> None:
    """只允许 loopback HTTP 与 HTTPS URL。"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
    except ValueError as exc:
        raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint") from exc
    if parsed.scheme == "https":
        if not host:
            raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")
        return
    if parsed.scheme != "http":
        raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")
    if not host:
        raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")
    if host == "localhost":
        return
    try:
        if ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    """读取 JSON object，且不跟随 redirect。"""
    ensure_allowed_url(url)
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False
        ) as resp:
            if 300 <= resp.status < 400:
                raise ClientError(f"不支持 HTTP redirect: {url}")
            if not 200 <= resp.status < 300:
                raise ClientError(f"HTTP {resp.status}: {url}")
            try:
                data = await resp.json()
            except (aiohttp.ContentTypeError, json.JSONDecodeError) as exc:
                raise ClientError(f"响应不是 JSON: {url}") from exc
    except ClientError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise ClientError(f"无法连接服务智能体: {url}") from exc
    if not isinstance(data, dict):
        raise ClientError(f"响应不是 JSON object: {url}")
    return data


def _interface_url_from_ad(ad: dict[str, Any], ad_url: str, endpoint: str) -> str:
    """从 Agent Description 选择 OpenRPC interface URL。"""
    interfaces = ad.get("interfaces")
    if isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            is_openrpc = (
                item.get("protocol") == "openrpc" or item.get("type") == "openrpc"
            )
            if is_openrpc and isinstance(item.get("url"), str):
                return urljoin(ad_url, item["url"])
    return f"{endpoint}/agent/interface.json"


def _rpc_endpoint_from_interface(
    interface_doc: dict[str, Any], interface_url: str, normalized_endpoint: str
) -> str:
    """从 OpenRPC servers 中选择 RPC endpoint。"""
    servers = interface_doc.get("servers")
    if isinstance(servers, list):
        for server in servers:
            if isinstance(server, dict) and isinstance(server.get("url"), str):
                return urljoin(interface_url, server["url"])
    return f"{normalized_endpoint}/agent/rpc"


def _methods_from_interface(interface_doc: dict[str, Any]) -> list[str]:
    """从 OpenRPC 文档中提取方法名。"""
    methods = interface_doc.get("methods")
    if not isinstance(methods, list):
        return []
    names: list[str] = []
    for method in methods:
        if isinstance(method, dict) and isinstance(method.get("name"), str):
            names.append(method["name"])
    return names


async def discover_service(
    endpoint: str | None,
    ad_url: str | None,
    require_chat: bool = False,
) -> ServiceInfo:
    """发现服务智能体；按需确认 chat 方法存在。"""
    if bool(endpoint) == bool(ad_url):
        raise ClientError("必须且只能提供 --endpoint 或 --ad-url")

    if endpoint:
        normalized_endpoint = normalize_endpoint(endpoint)
        ensure_allowed_url(normalized_endpoint)
        resolved_ad_url = f"{normalized_endpoint}/agent/ad.json"
    else:
        resolved_ad_url = ad_url or ""
        ensure_allowed_url(resolved_ad_url)
        normalized_endpoint = ""

    async with aiohttp.ClientSession() as session:
        ad = await _fetch_json(session, resolved_ad_url)
        if ad.get("protocolType") != "ANP":
            raise ClientError("目标不是 ANP 服务智能体")

        service_did = ad.get("did") or ad.get("id")
        if not isinstance(service_did, str) or not service_did:
            raise ClientError("Agent Description 缺少服务 DID")

        name = ad.get("name") if isinstance(ad.get("name"), str) else "ANP 服务智能体"
        ad_endpoint = ad.get("endpoint")
        if not normalized_endpoint:
            if not isinstance(ad_endpoint, str) or not ad_endpoint:
                raise ClientError("Agent Description 缺少 RPC endpoint")
            normalized_endpoint = normalize_endpoint(ad_endpoint)
        ensure_allowed_url(normalized_endpoint)

        interface_url = _interface_url_from_ad(ad, resolved_ad_url, normalized_endpoint)
        ensure_allowed_url(interface_url)
        interface_doc = await _fetch_json(session, interface_url)
        rpc_endpoint = _rpc_endpoint_from_interface(
            interface_doc, interface_url, normalized_endpoint
        )
        ensure_allowed_url(rpc_endpoint)
        methods = _methods_from_interface(interface_doc)
        if require_chat and "chat" not in methods:
            method_list = ", ".join(methods) if methods else "(none)"
            raise ClientError(f"服务智能体未声明 chat 方法；已发现方法: {method_list}")

        return ServiceInfo(
            service_did=service_did,
            name=name,
            rpc_endpoint=rpc_endpoint,
            interface_url=interface_url,
            methods=methods,
        )


def build_chat_body(message: str, request_id: str | None = None) -> tuple[str, str]:
    """构造 legacy params.message JSON-RPC chat body。"""
    rpc_id = request_id or f"chat-{uuid4().hex}"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "chat",
            "params": {"message": message},
        },
        ensure_ascii=False,
    )
    return body, rpc_id


def format_rpc_error(error: dict[str, Any]) -> str:
    """格式化 JSON-RPC error，并附加常见 DID WBA 故障提示。"""
    code = error.get("code")
    message = error.get("message", "未知错误")
    lines = [f"JSON-RPC error {code}: {message}"]
    if code == -32002:
        lines.append(
            "请先运行 serve-did，并在本地服务智能体设置 ANP_DID_RESOLVER_BASE_URL。"
        )
    elif code == -32001:
        lines.append(
            "请检查个人智能体 DID、私钥、签名 body 与服务端 DID 文档解析结果是否匹配。"
        )
    elif code == -32003:
        lines.append("必须通过 chat 命令发送 DID WBA 签名请求，而不是裸 HTTP 请求。")
    data = error.get("data")
    if data is not None:
        lines.append(f"data: {data}")
    return "\n".join(lines)


async def _post_chat_json(
    session: aiohttp.ClientSession,
    url: str,
    body: str,
    headers: dict[str, str],
) -> tuple[dict[str, Any], int]:
    """发送 chat JSON-RPC POST，并把 HTTP/JSON 错误转为 ClientError。"""
    ensure_allowed_url(url)
    try:
        async with session.post(
            url,
            data=body,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
            allow_redirects=False,
        ) as resp:
            if 300 <= resp.status < 400:
                raise ClientError(f"不支持 HTTP redirect: {url}")
            if not 200 <= resp.status < 300:
                raise ClientError(f"HTTP {resp.status}: {url}")
            try:
                data = await resp.json()
            except (aiohttp.ContentTypeError, json.JSONDecodeError) as exc:
                raise ClientError(f"响应不是 JSON: {url}") from exc
            return data, resp.status
    except ClientError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise ClientError(f"无法连接服务智能体: {url}") from exc


async def chat_service(
    endpoint: str | None, ad_url: str | None, message: str
) -> dict[str, Any]:
    """发现服务智能体并发送 DID WBA 签名 chat。"""
    identity = load_or_create_identity()
    service = await discover_service(
        endpoint=endpoint, ad_url=ad_url, require_chat=True
    )
    body, rpc_id = build_chat_body(message)
    headers = await build_signed_headers(identity, service.rpc_endpoint, body)

    async with aiohttp.ClientSession() as session:
        response_body, http_status = await _post_chat_json(
            session, service.rpc_endpoint, body, headers
        )

    if not isinstance(response_body, dict):
        raise ClientError("服务智能体响应不是 JSON object")
    if response_body.get("error") is not None:
        error = response_body["error"]
        if isinstance(error, dict):
            raise ClientError(format_rpc_error(error), exit_code=1)
        raise ClientError("服务智能体返回无法解析的 JSON-RPC error", exit_code=1)
    result = response_body.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise ClientError("服务智能体响应缺少 result.response", exit_code=1)

    return {
        "service_did": service.service_did,
        "caller_did": identity.did,
        "http_status": http_status,
        "jsonrpc_id": response_body.get("id", rpc_id),
        "response": result["response"],
    }


def _parse_port(value: str) -> int:
    """解析 TCP 端口号。"""
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("端口必须是整数") from exc


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="anp_client.py",
        description="个人智能体调用 ANP 服务智能体的客户端工具。",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("whoami", help="显示或创建个人智能体 DID")

    serve = subcommands.add_parser("serve-did", help="启动本地 DID 文档服务")
    serve.add_argument(
        "--host", default=os.environ.get("ANP_DID_SERVER_HOST", "127.0.0.1")
    )
    serve.add_argument(
        "--port",
        type=_parse_port,
        default=os.environ.get("ANP_DID_SERVER_PORT", "18900"),
    )
    serve.add_argument(
        "--check-only", action="store_true", help="只校验配置，不启动长驻服务"
    )

    discover = subcommands.add_parser("discover", help="发现 ANP 服务智能体")
    discover.add_argument("--endpoint")
    discover.add_argument("--ad-url")
    discover.add_argument("--json", action="store_true")

    chat = subcommands.add_parser("chat", help="向 ANP 服务智能体发送 chat")
    chat.add_argument("--endpoint")
    chat.add_argument("--ad-url")
    chat.add_argument("--message", required=True)
    chat.add_argument("--json", action="store_true")
    return parser


def _cmd_whoami() -> int:
    identity = load_or_create_identity()
    print(f"个人智能体 DID: {identity.did}")
    print(f"身份目录: {identity.did_path.parent}")
    print(f"DID 文档: {identity.did_path}")
    print(f"私钥: {identity.key_path}")
    return 0


async def _cmd_serve_did(args: argparse.Namespace) -> int:
    if not is_loopback_host(args.host):
        print("serve-did 第一期仅支持 loopback 监听地址", file=sys.stderr)
        return 2
    identity = load_or_create_identity()
    if args.check_only:
        print(f"个人智能体 DID: {identity.did}")
        print("serve-did 配置检查通过")
        return 0
    return await serve_did_document(identity, host=args.host, port=args.port)


async def _cmd_discover(args: argparse.Namespace) -> int:
    """执行 discover 子命令。"""
    service = await discover_service(endpoint=args.endpoint, ad_url=args.ad_url)
    if args.json:
        print(json.dumps(service.to_json(), ensure_ascii=False))
        return 0
    print(f"服务智能体: {service.name}")
    print(f"服务 DID: {service.service_did}")
    print(f"RPC endpoint: {service.rpc_endpoint}")
    print(f"OpenRPC interface: {service.interface_url}")
    print("可用方法:")
    for method in service.methods:
        print(f"  - {method}")
    return 0


async def _cmd_chat(args: argparse.Namespace) -> int:
    """执行 chat 子命令。"""
    result = await chat_service(
        endpoint=args.endpoint, ad_url=args.ad_url, message=args.message
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return 0
    print(f"服务 DID: {result['service_did']}")
    print(f"个人智能体 DID: {result['caller_did']}")
    print("\n回复:")
    print(result["response"])
    return 0


def main() -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "whoami":
            return _cmd_whoami()
        if args.command == "serve-did":
            return asyncio.run(_cmd_serve_did(args))
        if args.command == "discover":
            return asyncio.run(_cmd_discover(args))
        if args.command == "chat":
            return asyncio.run(_cmd_chat(args))
        parser.error(f"命令尚未实现: {args.command}")
        return 2
    except ClientError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    except IdentityError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
