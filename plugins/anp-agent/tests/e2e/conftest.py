"""E2E 测试共享配置与 fixtures。"""

from __future__ import annotations

from pathlib import Path

import pytest


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
