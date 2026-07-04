"""E2E 回声功能冒烟测试。"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
async def test_anp_agent_echo_skill_smoke():
    """验证 ANP Agent 的 echo skill 可通过 JSON-RPC 调用并返回响应。"""
    pass
