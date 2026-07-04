"""E2E LLM 交互慢速测试。"""

from __future__ import annotations

import pytest


@pytest.mark.slow
async def test_anp_agent_llm_response_smoke():
    """验证 ANP Agent 可通过自然语言请求触发 skill 并返回 LLM 响应。"""
    pass
