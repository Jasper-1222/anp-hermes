"""anp-client skill 测试配置。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from aiohttp.test_utils import unused_port

CLIENT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = CLIENT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def client_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """为测试隔离 ANP_CLIENT_HOME。"""
    home = tmp_path / "anp-client-home"
    monkeypatch.setenv("ANP_CLIENT_HOME", str(home))
    return home


@pytest.fixture
def aiohttp_unused_port() -> Callable[[], int]:
    """提供空闲端口 fixture，复用 aiohttp 自带 helper，避免新增 pytest-aiohttp 依赖。"""
    return unused_port
