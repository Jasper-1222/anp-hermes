"""ANP 插件配置加载模块的单元测试。"""

from pathlib import Path
from types import SimpleNamespace

from anp_agent.config import ANPConfig, load_config


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
        "ANP_TOOL_RPC_ENABLED",
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
    assert cfg.data_dir == str(Path.home() / ".hermes" / "data" / "anp-agent")
    assert cfg.request_timeout == 60
    assert cfg.future_ttl == 120
    assert cfg.tool_rpc.enabled is False
    assert cfg.tool_rpc.allowed_dids == ()
    assert cfg.tool_rpc.allowed_tools == ()
    assert cfg.tool_rpc.allowed_toolsets == ()
    assert cfg.tool_rpc.denied_tools == ()
    assert cfg.tool_rpc.timeout_seconds == 30
    assert cfg.tool_rpc.max_result_bytes == 65536
    assert cfg.tool_rpc.has_allowlist is False


def test_tool_rpc_extra_loads_policy_fields(monkeypatch):
    """tool_rpc 配置应从 extra 中加载显式策略字段。"""
    _clear_env(monkeypatch)
    extra = {
        "tool_rpc": {
            "enabled": True,
            "allowed_dids": ["did:wba:localhost:agent:caller"],
            "allowed_tools": ["safe_tool"],
            "allowed_toolsets": ["readonly"],
            "denied_tools": ["blocked_tool"],
            "timeout_seconds": "12",
            "max_result_bytes": "4096",
        }
    }

    cfg = load_config(_platform_config(extra))

    assert cfg.tool_rpc.enabled is True
    assert cfg.tool_rpc.allowed_dids == ("did:wba:localhost:agent:caller",)
    assert cfg.tool_rpc.allowed_tools == ("safe_tool",)
    assert cfg.tool_rpc.allowed_toolsets == ("readonly",)
    assert cfg.tool_rpc.denied_tools == ("blocked_tool",)
    assert cfg.tool_rpc.timeout_seconds == 12
    assert cfg.tool_rpc.max_result_bytes == 4096
    assert cfg.tool_rpc.has_allowlist is True


def test_tool_rpc_enabled_without_allowlist_has_no_allowlist(monkeypatch):
    """仅开启 tool_rpc 但未配置工具 allowlist 时不应形成可暴露能力。"""
    _clear_env(monkeypatch)

    cfg = load_config(_platform_config({"tool_rpc": {"enabled": True}}))

    assert cfg.tool_rpc.enabled is True
    assert cfg.tool_rpc.has_allowlist is False


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
    monkeypatch.setenv("ANP_DATA_DIR", "/tmp/env-anp-data")
    extra = {
        "port": "4444",
        "hostname": "extra.example.com",
        "data_dir": "/tmp/extra-anp-data",
    }

    cfg = load_config(_platform_config(extra))

    assert cfg.port == 3333
    assert cfg.hostname == "env.example.com"
    assert cfg.data_dir == "/tmp/env-anp-data"


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
