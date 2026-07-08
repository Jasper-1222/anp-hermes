"""ANP 插件配置加载模块。

本模块通过 duck typing 读取 Hermes 传入的平台配置对象，
避免直接依赖 Hermes 内部类型。
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import constants


@dataclass(frozen=True)
class ToolRPCConfig:
    """Hermes tools 通过 ANP RPC 暴露的安全配置。"""

    enabled: bool = False
    allowed_dids: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    allowed_toolsets: tuple[str, ...] = ()
    denied_tools: tuple[str, ...] = ()
    timeout_seconds: int = 30
    max_result_bytes: int = 65536

    @property
    def has_allowlist(self) -> bool:
        """是否配置了至少一个工具或工具集 allowlist。"""
        return bool(self.allowed_tools or self.allowed_toolsets)


@dataclass(frozen=True)
class ANPConfig:
    """ANP 插件的运行时配置。"""

    host: str
    port: int
    hostname: str
    endpoint: str
    data_dir: str
    request_timeout: int
    future_ttl: int
    tool_rpc: ToolRPCConfig = ToolRPCConfig()

    def replace(self, **kwargs) -> "ANPConfig":
        """返回一份替换指定字段后的新配置。"""
        return ANPConfig(
            host=kwargs.get("host", self.host),
            port=kwargs.get("port", self.port),
            hostname=kwargs.get("hostname", self.hostname),
            endpoint=kwargs.get("endpoint", self.endpoint),
            data_dir=kwargs.get("data_dir", self.data_dir),
            request_timeout=kwargs.get("request_timeout", self.request_timeout),
            future_ttl=kwargs.get("future_ttl", self.future_ttl),
            tool_rpc=kwargs.get("tool_rpc", self.tool_rpc),
        )


def _get_str(extra: dict, env_name: str, key: str, default: str) -> str:
    """读取字符串配置项，环境变量优先级高于 extra。"""
    value = os.environ.get(env_name)
    if value is not None:
        return value
    value = extra.get(key)
    if value is not None:
        return str(value)
    return default


def _get_int(extra: dict, env_name: str, key: str, default: int) -> int:
    """读取整数配置项，转换失败时回退默认值。"""
    raw = os.environ.get(env_name)
    if raw is None:
        raw = extra.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _get_path(extra: dict, env_name: str, key: str, default: str) -> str:
    """读取路径配置项，并将 ~ 展开为用户主目录。"""
    value = _get_str(extra, env_name, key, default)
    return str(Path(value).expanduser())


def _get_bool(extra: dict, env_name: str, key: str, default: bool) -> bool:
    """读取布尔配置项，支持常见字符串形态。"""
    raw = os.environ.get(env_name)
    if raw is None:
        raw = extra.get(key)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        return raw != 0
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off", ""}:
        return False
    return default


def _get_tuple(value: Any) -> tuple[str, ...]:
    """将列表或逗号分隔字符串配置归一化为字符串 tuple。"""
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = (value,)
    return tuple(str(item).strip() for item in items if str(item).strip())


def _load_tool_rpc_config(extra: dict) -> ToolRPCConfig:
    """从 extra.tool_rpc 加载 Hermes tool RPC 安全配置。"""
    raw = extra.get("tool_rpc")
    tool_extra = raw if isinstance(raw, dict) else {}
    return ToolRPCConfig(
        enabled=_get_bool(tool_extra, "ANP_TOOL_RPC_ENABLED", "enabled", False),
        allowed_dids=_get_tuple(tool_extra.get("allowed_dids")),
        allowed_tools=_get_tuple(tool_extra.get("allowed_tools")),
        allowed_toolsets=_get_tuple(tool_extra.get("allowed_toolsets")),
        denied_tools=_get_tuple(tool_extra.get("denied_tools")),
        timeout_seconds=_get_int(tool_extra, "ANP_TOOL_RPC_TIMEOUT", "timeout_seconds", 30),
        max_result_bytes=_get_int(
            tool_extra,
            "ANP_TOOL_RPC_MAX_RESULT_BYTES",
            "max_result_bytes",
            65536,
        ),
    )


def load_config(platform_config) -> ANPConfig:
    """从 platform_config.extra 和环境变量加载配置。"""
    extra = getattr(platform_config, "extra", None) or {}

    host = _get_str(extra, "ANP_HOST", "host", constants.DEFAULT_HOST)
    port = _get_int(extra, "ANP_PORT", "port", constants.DEFAULT_PORT)
    hostname = _get_str(extra, "ANP_HOSTNAME", "hostname", constants.DEFAULT_HOSTNAME)
    data_dir = _get_path(extra, "ANP_DATA_DIR", "data_dir", constants.DEFAULT_DATA_DIR)

    endpoint = _get_str(extra, "ANP_ENDPOINT", "endpoint", "")
    if not endpoint:
        endpoint = f"http://{hostname}:{port}"

    request_timeout = _get_int(
        extra,
        "ANP_REQUEST_TIMEOUT",
        "request_timeout",
        constants.DEFAULT_REQUEST_TIMEOUT,
    )
    future_ttl = _get_int(extra, "ANP_FUTURE_TTL", "future_ttl", constants.DEFAULT_FUTURE_TTL)

    return ANPConfig(
        host=host,
        port=port,
        hostname=hostname,
        endpoint=endpoint,
        data_dir=data_dir,
        request_timeout=request_timeout,
        future_ttl=future_ttl,
        tool_rpc=_load_tool_rpc_config(extra),
    )
