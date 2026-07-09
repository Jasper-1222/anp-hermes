"""SKILL.md 自然语言样例解析契约测试。"""

from __future__ import annotations

import pytest

from anp_client import ClientError, normalize_natural_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "通过 ANP 调用 http://127.0.0.1:8900 的服务智能体，问它“你好”",
            {"action": "chat", "endpoint": "http://127.0.0.1:8900", "message": "你好"},
        ),
        (
            "请连接 http://127.0.0.1:8900/agent/ad.json 并发送：你好",
            {
                "action": "chat",
                "ad_url": "http://127.0.0.1:8900/agent/ad.json",
                "message": "你好",
            },
        ),
        (
            "用 ANP client 向 http://127.0.0.1:8900 发送 hello",
            {"action": "chat", "endpoint": "http://127.0.0.1:8900", "message": "hello"},
        ),
        (
            "发现 http://127.0.0.1:8900 的 ANP 服务智能体",
            {"action": "discover", "endpoint": "http://127.0.0.1:8900"},
        ),
    ],
)
def test_normalize_natural_language_examples(
    text: str, expected: dict[str, str]
) -> None:
    assert normalize_natural_language(text) == expected


def test_normalize_natural_language_rejects_missing_url() -> None:
    with pytest.raises(ClientError, match="未找到 ANP 服务 URL"):
        normalize_natural_language("问它你好")
