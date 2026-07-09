#!/usr/bin/env python3
"""通用 ANP client skill 命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from did_identity import IdentityError, load_or_create_identity
from did_server import is_loopback_host, serve_did_document


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="anp_client.py",
        description="个人智能体调用 ANP 服务智能体的客户端工具。",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("whoami", help="显示或创建个人智能体 DID")

    serve = subcommands.add_parser("serve-did", help="启动本地 DID 文档服务")
    serve.add_argument("--host", default=os.environ.get("ANP_DID_SERVER_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("ANP_DID_SERVER_PORT", "18900")))
    serve.add_argument("--check-only", action="store_true", help="只校验配置，不启动长驻服务")

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


def main() -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "whoami":
            return _cmd_whoami()
        if args.command == "serve-did":
            return asyncio.run(_cmd_serve_did(args))
        parser.error(f"命令尚未实现: {args.command}")
        return 2
    except IdentityError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
