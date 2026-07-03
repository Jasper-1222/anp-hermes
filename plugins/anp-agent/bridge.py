"""ANP RPC 桥接层。

本模块负责将 ANP JSON-RPC 请求转换为 Hermes 的 MessageEvent，
并通过 asyncio.Future 等待 Hermes 核心处理完成后返回结果。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config import ANPConfig

logger = logging.getLogger(__name__)


@dataclass
class MessageEvent:
    """Hermes handle_message 所需的最小事件结构（duck typing）。"""

    text: str
    message_type: str = "text"
    source: Any = None
    raw_message: Any = None
    message_id: str | None = None
    platform_update_id: int | None = None
    media_urls: list[str] = field(default_factory=list)
    media_types: list[str] = field(default_factory=list)
    reply_to_message_id: str | None = None
    reply_to_text: str | None = None
    reply_to_author_id: str | None = None
    reply_to_author_name: str | None = None
    reply_to_is_own_message: bool = False
    auto_skill: str | list[str] | None = None
    channel_prompt: str | None = None
    channel_context: str | None = None
    internal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class _PendingFuture:
    """内部包装：记录 Future 及其创建时间，用于 TTL 清理。"""

    future: asyncio.Future[str]
    created_at: datetime = field(default_factory=datetime.now)


class ANPBridge:
    """ANP 与 Hermes 之间的 RPC 桥接器。

    不依赖 Hermes 具体类型，仅通过 message_handler callable 将 MessageEvent 提交给上层。
    """

    def __init__(
        self,
        config: ANPConfig,
        message_handler: Callable[[MessageEvent], None],
        max_pending: int = 1024,
    ) -> None:
        """构造桥接器。

        Args:
            config: ANP 插件配置，其中 request_timeout 与 future_ttl 会被使用。
            message_handler: 上层消息处理回调，接收 MessageEvent。
            max_pending: 同时等待的最大 pending Future 数量。
        """
        self._config = config
        self._message_handler = message_handler
        self._max_pending = max_pending
        self._pending: dict[str, _PendingFuture] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动后台 TTL 清理任务。"""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.debug("ANPBridge 清理任务已启动")

    async def stop(self) -> None:
        """停止后台清理任务并取消所有未完成的 futures。"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.debug("ANPBridge 清理任务已停止")

        for entry in list(self._pending.values()):
            if not entry.future.done():
                entry.future.cancel()
        self._pending.clear()
        # 让正在等待的 call() 任务有机会观察到 Future 取消并结束
        await asyncio.sleep(0)

    async def call(
        self,
        rpc_id: str,
        method: str,
        params: dict[str, Any],
        caller_did: str,
    ) -> str:
        """发起一次 ANP JSON-RPC 调用，等待 Hermes 返回结果。

        Args:
            rpc_id: JSON-RPC 请求 id，用于关联结果。
            method: JSON-RPC method 字段。
            params: JSON-RPC params 字段。
            caller_did: 调用方 DID，写入事件元数据。

        Returns:
            Hermes 处理后的回复文本；超时或异常时返回通用错误信息。

        Raises:
            ValueError: rpc_id 已在 pending 中。
            RuntimeError: pending futures 数量已达上限。
        """
        if rpc_id in self._pending:
            raise ValueError(f"重复的 rpc_id: {rpc_id}")

        self._cleanup_expired()

        if len(self._pending) >= self._max_pending:
            raise RuntimeError("pending futures 数量已达上限")

        event = MessageEvent(
            text=params.get("message", ""),
            message_id=rpc_id,
            metadata={
                "anp_rpc_id": rpc_id,
                "anp_method": method,
                "anp_params": params,
                "anp_caller_did": caller_did,
            },
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[rpc_id] = _PendingFuture(future=future)

        try:
            self._message_handler(event)
        except Exception as exc:  # pragma: no cover - handler 异常不应影响 bridge
            logger.exception("message_handler 调用失败: %s", exc)
            self._pending.pop(rpc_id, None)
            future.cancel()
            return "内部错误：无法将请求提交给 Hermes"

        try:
            result = await asyncio.wait_for(future, timeout=self._config.request_timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning("rpc_id=%s 等待结果超时", rpc_id)
            self._pending.pop(rpc_id, None)
            return "请求处理超时，请稍后重试"
        except asyncio.CancelledError:
            logger.debug("rpc_id=%s 的 Future 被取消", rpc_id)
            self._pending.pop(rpc_id, None)
            return "请求已取消"
        except Exception as exc:
            logger.exception("等待 rpc_id=%s 结果时发生异常: %s", rpc_id, exc)
            self._pending.pop(rpc_id, None)
            return "请求处理过程中发生内部错误"

    def set_result(self, rpc_id: str, content: str) -> bool:
        """根据 rpc_id 设置对应 pending Future 的结果。

        Args:
            rpc_id: JSON-RPC 请求 id。
            content: Hermes 返回的文本内容。

        Returns:
            是否成功找到并设置结果。
        """
        entry = self._pending.pop(rpc_id, None)
        if entry is None:
            logger.debug("rpc_id=%s 无对应 pending future", rpc_id)
            return False
        if entry.future.done():
            return False
        entry.future.set_result(content)
        return True

    def _cleanup_expired(self) -> None:
        """清理超过 future_ttl 的 pending futures。"""
        now = datetime.now()
        ttl = self._config.future_ttl
        expired_keys = [
            rpc_id
            for rpc_id, entry in self._pending.items()
            if (now - entry.created_at).total_seconds() >= ttl
        ]
        for rpc_id in expired_keys:
            entry = self._pending.pop(rpc_id, None)
            if entry is not None and not entry.future.done():
                entry.future.set_exception(asyncio.TimeoutError("pending future 已过期"))
            logger.debug("清理过期 pending future: rpc_id=%s", rpc_id)

    async def _cleanup_loop(self) -> None:
        """后台循环：定期清理过期 pending futures。"""
        try:
            while True:
                await asyncio.sleep(max(1, self._config.future_ttl // 2))
                self._cleanup_expired()
        except asyncio.CancelledError:
            logger.debug("ANPBridge 清理循环已取消")
            raise
