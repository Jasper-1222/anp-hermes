"""ANP 插件配置加载模块。

本模块通过 duck typing 读取 Hermes 传入的平台配置对象，
避免直接依赖 Hermes 内部类型。
"""

import os
from dataclasses import dataclass
from pathlib import Path

import constants


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
    )
