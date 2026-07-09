#!/usr/bin/env python3
"""通用 ANP client skill 命令行入口。"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="anp_client.py",
        description="个人智能体调用 ANP 服务智能体的客户端工具。",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("whoami", help="显示或创建个人智能体 DID")
    subcommands.add_parser("serve-did", help="启动本地 DID 文档服务")

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


def main() -> int:
    """CLI 入口。"""
    parser = build_parser()
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
