"""ANP Agent 平台插件入口。"""

import sys
from pathlib import Path
from typing import Any

# Hermes 以 namespace package 加载本插件，插件目录不会自动进入 sys.path，
# 因此需要显式加入，以保证插件内部各模块的绝对导入可解析。
sys.path.insert(0, str(Path(__file__).resolve().parent))

_REQUIRED_ENV = ["ANP_ALLOW_ALL_USERS"]


def register(ctx: Any) -> None:
    """注册 ANP 平台适配器到 Hermes 插件上下文。

    Args:
        ctx: Hermes 插件上下文对象。
    """
    from adapter import ANPAdapter

    ctx.register_platform(
        name="anp",
        label="ANP Agent",
        adapter_factory=lambda cfg: ANPAdapter(cfg),
        check_fn=lambda: True,
        required_env=_REQUIRED_ENV,
        emoji="🌐",
        platform_hint="ANP（Agent Network Protocol）服务智能体接入",
        allowed_users_env="ANP_ALLOWED_USERS",
        allow_all_env="ANP_ALLOW_ALL_USERS",
    )
