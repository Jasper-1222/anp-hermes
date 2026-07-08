"""E2E helper 函数基础测试。"""

from __future__ import annotations

from .conftest import free_port


def test_free_port_returns_valid_port():
    """free_port 应返回 1024-65535 范围内的整数。"""
    port = free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535
