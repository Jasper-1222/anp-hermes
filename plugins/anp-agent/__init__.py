"""ANP Agent 平台插件入口。"""

from typing import Any

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
    )
