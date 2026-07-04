"""ANP 插件配置加载模块的单元测试。"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ANPConfig, load_config


def _platform_config(extra=None):
    """构造一个仅提供 .extra 属性的极简平台配置对象。"""
    return SimpleNamespace(extra=extra or {})


def _clear_env(monkeypatch):
    """清除所有 ANP_ 前缀的环境变量，避免交叉测试污染。"""
    for name in (
        "ANP_HOST",
        "ANP_PORT",
        "ANP_HOSTNAME",
        "ANP_ENDPOINT",
        "ANP_DATA_DIR",
        "ANP_REQUEST_TIMEOUT",
        "ANP_FUTURE_TTL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_values(monkeypatch):
    """验证默认值。"""
    _clear_env(monkeypatch)

    cfg = load_config(_platform_config())

    assert isinstance(cfg, ANPConfig)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8900
    assert cfg.hostname == "localhost"
    assert cfg.endpoint == "http://localhost:8900"
    assert cfg.data_dir == str(Path.home() / ".hermes" / "plugins" / "anp-agent")
    assert cfg.request_timeout == 60
    assert cfg.future_ttl == 120


def test_env_variables_override_all_fields(monkeypatch):
    """环境变量应能覆盖所有配置字段。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANP_HOST", "127.0.0.1")
    monkeypatch.setenv("ANP_PORT", "9000")
    monkeypatch.setenv("ANP_HOSTNAME", "service.example.com")
    monkeypatch.setenv("ANP_ENDPOINT", "https://example.com/agent")
    monkeypatch.setenv("ANP_DATA_DIR", "/tmp/anp-data")
    monkeypatch.setenv("ANP_REQUEST_TIMEOUT", "30")
    monkeypatch.setenv("ANP_FUTURE_TTL", "45")

    cfg = load_config(_platform_config())

    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.hostname == "service.example.com"
    assert cfg.endpoint == "https://example.com/agent"
    assert cfg.data_dir == "/tmp/anp-data"
    assert cfg.request_timeout == 30
    assert cfg.future_ttl == 45


def test_extra_overrides_defaults():
    """config.yaml extra 中的配置应覆盖默认值。"""
    extra = {
        "host": "0.0.0.0",
        "port": "7000",
        "hostname": "extra.example.com",
        "endpoint": "http://extra.example.com:7000/agent",
        "data_dir": "/var/lib/anp",
        "request_timeout": "90",
        "future_ttl": "180",
    }

    cfg = load_config(_platform_config(extra))

    assert cfg.host == "0.0.0.0"
    assert cfg.port == 7000
    assert cfg.hostname == "extra.example.com"
    assert cfg.endpoint == "http://extra.example.com:7000/agent"
    assert cfg.data_dir == "/var/lib/anp"
    assert cfg.request_timeout == 90
    assert cfg.future_ttl == 180


def test_env_takes_precedence_over_extra(monkeypatch):
    """环境变量优先级高于 config.yaml extra。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANP_PORT", "3333")
    monkeypatch.setenv("ANP_HOSTNAME", "env.example.com")
    extra = {"port": "4444", "hostname": "extra.example.com"}

    cfg = load_config(_platform_config(extra))

    assert cfg.port == 3333
    assert cfg.hostname == "env.example.com"


def test_invalid_integer_falls_back_to_default(monkeypatch):
    """非法整数字符串应回退到默认值，且不抛出异常。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANP_PORT", "not-a-number")
    monkeypatch.setenv("ANP_REQUEST_TIMEOUT", "abc")
    monkeypatch.setenv("ANP_FUTURE_TTL", "")
    extra = {"port": "also-bad", "request_timeout": "", "future_ttl": "???"}

    cfg = load_config(_platform_config(extra))

    assert cfg.port == 8900
    assert cfg.request_timeout == 60
    assert cfg.future_ttl == 120


def test_data_dir_expands_tilde(monkeypatch):
    """data_dir 中的 ~ 应被正确展开为用户主目录。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANP_DATA_DIR", "~/anp-data")

    cfg = load_config(_platform_config())

    assert cfg.data_dir == str(Path.home() / "anp-data")
