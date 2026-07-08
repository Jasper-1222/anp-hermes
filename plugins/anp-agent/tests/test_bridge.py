"""ANP RPC 桥接层单元测试。"""

import asyncio

import pytest

from anp_agent.bridge import ANPBridge, ANPBridgeError, MessageEvent
from anp_agent.config import ANPConfig


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
    """call() 应返回 message_handler 通过内部 request id 设置的内容。"""
    bridge = None
    captured_event = None

    def handler(event: MessageEvent) -> None:
        nonlocal captured_event
        captured_event = event
        bridge.set_result(event.message_id, "你好，世界")

    config = _config(request_timeout=1)
    bridge = ANPBridge(config, handler)

    result = await bridge.call("rpc-1", "chat", {"message": "hi"}, "did:wba:alice")

    assert result == "你好，世界"
    assert captured_event is not None
    assert captured_event.message_id == "req-1"
    assert captured_event.metadata["anp_rpc_id"] == "rpc-1"
    assert captured_event.metadata["anp_request_id"] == "req-1"
    assert captured_event.metadata["anp_method"] == "chat"
    assert captured_event.metadata["anp_params"] == {"message": "hi"}
    assert captured_event.metadata["anp_caller_did"] == "did:wba:alice"
    assert "req-1" not in bridge._pending


@pytest.mark.asyncio
async def test_same_client_rpc_id_can_run_concurrently():
    """相同客户端 rpc_id 的并发调用应使用不同内部 request id 隔离。"""
    captured_events: list[MessageEvent] = []

    def handler(event: MessageEvent) -> None:
        captured_events.append(event)

    config = _config(request_timeout=10)
    bridge = ANPBridge(config, handler)

    first = asyncio.create_task(bridge.call("dup", "chat", {}, "did:wba:alice"))
    second = asyncio.create_task(bridge.call("dup", "chat", {}, "did:wba:bob"))
    await asyncio.sleep(0)

    assert sorted(bridge._pending.keys()) == ["req-1", "req-2"]
    assert [event.metadata["anp_rpc_id"] for event in captured_events] == ["dup", "dup"]
    assert [event.metadata["anp_request_id"] for event in captured_events] == [
        "req-1",
        "req-2",
    ]

    bridge.set_result("req-2", "bob-ok")
    bridge.set_result("req-1", "alice-ok")
    assert await first == "alice-ok"
    assert await second == "bob-ok"


@pytest.mark.asyncio
async def test_pending_capacity_limit_raises_bridge_error():
    """pending futures 超过上限时应抛出结构化 bridge 错误。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=60)
    bridge = ANPBridge(config, handler, max_pending=2)

    task1 = asyncio.create_task(bridge.call("a", "chat", {}, "did:wba:alice"))
    task2 = asyncio.create_task(bridge.call("b", "chat", {}, "did:wba:bob"))
    await asyncio.sleep(0)

    with pytest.raises(ANPBridgeError) as exc_info:
        await bridge.call("c", "chat", {}, "did:wba:charlie")

    assert exc_info.value.rpc_code == -32603
    assert "服务繁忙" in exc_info.value.message

    bridge.set_result("req-1", "r1")
    bridge.set_result("req-2", "r2")
    assert await task1 == "r1"
    assert await task2 == "r2"


@pytest.mark.asyncio
async def test_call_timeout_raises_bridge_error():
    """call() 超时后应抛出结构化 bridge 错误。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=1)
    bridge = ANPBridge(config, handler)

    with pytest.raises(ANPBridgeError) as exc_info:
        await bridge.call("to", "chat", {"message": "hi"}, "did:wba:alice")

    assert exc_info.value.rpc_code == -32603
    assert "超时" in exc_info.value.message
    assert "req-1" not in bridge._pending


@pytest.mark.asyncio
async def test_handler_exception_raises_bridge_error():
    """message_handler 异常应抛出结构化 bridge 错误。"""

    def handler(event: MessageEvent) -> None:
        raise RuntimeError("模拟提交失败")

    config = _config(request_timeout=1)
    bridge = ANPBridge(config, handler)

    with pytest.raises(ANPBridgeError) as exc_info:
        await bridge.call("err", "chat", {}, "did:wba:alice")

    assert exc_info.value.rpc_code == -32603
    assert "无法将请求提交给 Hermes" in exc_info.value.message
    assert "req-1" not in bridge._pending


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
        assert "req-1" in bridge._pending

        await asyncio.sleep(2.5)
        assert "req-1" not in bridge._pending

        with pytest.raises(ANPBridgeError) as exc_info:
            await asyncio.wait_for(task, timeout=2)
        assert exc_info.value.rpc_code == -32603
    finally:
        await bridge.stop()


@pytest.mark.asyncio
async def test_stop_cancels_unfinished_futures():
    """stop() 应取消所有未完成的 futures 并让等待者收到结构化错误。"""

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
    for task in (task1, task2):
        with pytest.raises(ANPBridgeError) as exc_info:
            await task
        assert "取消" in exc_info.value.message


@pytest.mark.asyncio
async def test_external_task_cancellation_is_not_wrapped():
    """外部取消 call() 任务时应保留 asyncio cancellation 语义。"""

    def handler(event: MessageEvent) -> None:
        pass

    config = _config(request_timeout=60)
    bridge = ANPBridge(config, handler)

    task = asyncio.create_task(bridge.call("x", "chat", {}, "did:wba:alice"))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(bridge._pending) == 0
