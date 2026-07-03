"""ANP RPC 桥接层单元测试。"""

import asyncio
import os
import sys

import pytest

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge import ANPBridge, MessageEvent
from config import ANPConfig


def _config(**kwargs) -> ANPConfig:
    """构造测试用的 ANPConfig，未指定字段使用较小值以缩短测试时间。"""
    defaults = {
        "host": "0.0.0.0",
        "port": 8900,
        "hostname": "localhost",
        "endpoint": "http://localhost:8900",
        "data_dir": "/tmp/anp-test",
        "request_timeout": 60,
        "future_ttl": 120,
    }
    defaults.update(kwargs)
    return ANPConfig(**defaults)


@pytest.mark.asyncio
async def test_call_returns_handler_set_content():
    """call() 应返回 message_handler 通过 set_result 设置的内容。"""
    bridge = None

    def handler(event: MessageEvent) -> None:
        bridge.set_result(event.message_id, "你好，世界")

    config = _config(request_timeout=1)
    bridge = ANPBridge(config, handler)

    result = await bridge.call("rpc-1", "chat", {"message": "hi"}, "did:wba:alice")

    assert result == "你好，世界"
    assert "rpc-1" not in bridge._pending


@pytest.mark.asyncio
async def test_duplicate_rpc_id_raises_value_error():
    """重复 rpc_id 应抛出 ValueError。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=10)
    bridge = ANPBridge(config, handler)

    first = asyncio.create_task(bridge.call("dup", "chat", {}, "did:wba:alice"))
    await asyncio.sleep(0)  # 让第一次调用注册 pending

    with pytest.raises(ValueError):
        await bridge.call("dup", "chat", {}, "did:wba:bob")

    bridge.set_result("dup", "ok")
    assert await first == "ok"


@pytest.mark.asyncio
async def test_pending_capacity_limit_raises_runtime_error():
    """pending futures 超过上限时应抛出 RuntimeError。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=60)
    bridge = ANPBridge(config, handler)
    bridge._max_pending = 2

    task1 = asyncio.create_task(bridge.call("a", "chat", {}, "did:wba:alice"))
    task2 = asyncio.create_task(bridge.call("b", "chat", {}, "did:wba:bob"))
    await asyncio.sleep(0)

    with pytest.raises(RuntimeError):
        await bridge.call("c", "chat", {}, "did:wba:charlie")

    bridge.set_result("a", "r1")
    bridge.set_result("b", "r2")
    assert await task1 == "r1"
    assert await task2 == "r2"


@pytest.mark.asyncio
async def test_call_timeout_returns_error():
    """call() 超时后应返回通用超时错误，而非抛出未处理异常。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=1)
    bridge = ANPBridge(config, handler)

    result = await bridge.call("to", "chat", {"message": "hi"}, "did:wba:alice")

    assert "超时" in result
    assert "to" not in bridge._pending


@pytest.mark.asyncio
async def test_cleanup_removes_expired_futures():
    """后台 TTL 清理应移除过期的 pending futures。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(future_ttl=1)
    bridge = ANPBridge(config, handler)
    await bridge.start()

    try:
        task = asyncio.create_task(bridge.call("exp", "chat", {}, "did:wba:alice"))
        await asyncio.sleep(0)
        assert "exp" in bridge._pending

        await asyncio.sleep(1.5)
        assert "exp" not in bridge._pending

        result = await asyncio.wait_for(task, timeout=2)
        assert "超时" in result or "过期" in result or "内部错误" in result
    finally:
        await bridge.stop()


@pytest.mark.asyncio
async def test_stop_cancels_unfinished_futures():
    """stop() 应取消所有未完成的 futures 并清空 pending。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=60)
    bridge = ANPBridge(config, handler)
    await bridge.start()

    task1 = asyncio.create_task(bridge.call("x", "chat", {}, "did:wba:alice"))
    task2 = asyncio.create_task(bridge.call("y", "chat", {}, "did:wba:bob"))
    await asyncio.sleep(0)
    assert len(bridge._pending) == 2

    await bridge.stop()

    assert len(bridge._pending) == 0
    assert task1.done()
    assert task2.done()
