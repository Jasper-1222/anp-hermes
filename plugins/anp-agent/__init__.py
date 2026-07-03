"""ANP Agent 平台插件入口。"""

from adapter import ANPAdapter


def register(ctx):
    """注册 ANP 平台适配器到 Hermes 插件上下文。

    Args:
        ctx: Hermes 插件上下文对象。
    """
    ctx.register_platform(
        name="anp",
        label="ANP Agent",
        adapter_factory=lambda cfg: ANPAdapter(cfg),
        check_fn=lambda: True,
    )
