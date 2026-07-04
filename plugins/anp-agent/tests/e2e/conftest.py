"""E2E 测试共享配置与 fixtures。"""

from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Any

import pytest
import requests
import yaml


def pytest_addoption(parser):
    """注册 E2E 测试选项。"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="运行 E2E 测试（需要本地 Hermes 安装）",
    )
    parser.addoption(
        "--run-slow-e2e",
        action="store_true",
        default=False,
        help="运行需要真实 LLM 的慢速 E2E 测试",
    )


def pytest_collection_modifyitems(config, items):
    """未传 --run-e2e 时跳过 e2e 目录下所有测试。"""
    if config.getoption("--run-e2e"):
        return
    skip = pytest.mark.skip(reason="需要 --run-e2e 选项才能运行 E2E 测试")
    e2e_root = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(e2e_root):
            item.add_marker(skip)


def free_port() -> int:
    """申请一个本地空闲 TCP 端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_url(url: str, timeout: float = 60.0, interval: float = 0.5) -> bool:
    """轮询等待 URL 返回 HTTP 200。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def _load_user_hermes_config() -> dict[str, Any]:
    """读取用户真实 ~/.hermes/config.yaml 的 model/provider 配置。

    如果文件不存在或解析失败，返回空字典。
    """
    config_path = Path.home() / ".hermes" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}
