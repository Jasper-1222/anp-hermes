"""ANP 平台适配器实现。

本模块实现 Hermes 平台适配器生命周期，将 ANP 身份、认证、RPC 桥接与 aiohttp 服务器串联起来。
"""

import logging
from typing import Any

from aiohttp import web
from gateway.config import Platform
from gateway.platforms.base import BasePlatformAdapter, SendResult

from auth import create_auth
from bridge import ANPBridge
from config import load_config
from identity import load_or_create_identity
from server import create_app

logger = logging.getLogger(__name__)


class ANPAdapter(BasePlatformAdapter):
    """ANP 平台适配器。"""

    def __init__(self, config):
        """构造适配器。

        Args:
            config: Hermes PlatformConfig 对象，通过 load_config 转换为 ANPConfig。
        """
        platform = Platform("anp")
        super().__init__(config=config, platform=platform)
        self._anp_config = load_config(config)
        self._identity = None
        self._auth = None
        self._bridge = None
        self._app = None
        self._runner = None

    async def connect(self, *, is_reconnect=False) -> bool:
        """连接平台：加载身份、创建认证与桥接、启动 aiohttp 服务器与桥接任务。

        Args:
            is_reconnect: Hermes 重连标志，本实现中忽略。

        Returns:
            是否连接成功。
        """
        # 加载或创建 DID WBA 身份
        self._identity = load_or_create_identity(
            self._anp_config.data_dir, self._anp_config.hostname
        )

        # 创建服务端认证器
        self._auth = create_auth(self._identity)

        # 创建 RPC 桥接器，将 Hermes handle_message 作为消息处理入口
        self._bridge = ANPBridge(
            config=self._anp_config,
            message_handler=self.handle_message,
        )

        # 启动 aiohttp 服务器
        self._app = create_app(
            config=self._anp_config,
            identity=self._identity,
            auth=self._auth,
            bridge=self._bridge,
        )
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner,
            host=self._anp_config.host,
            port=self._anp_config.port,
        )
        await site.start()
        # 获取实际绑定的地址，port=0 时尤其需要
        addresses = [f"{addr[0]}:{addr[1]}" for addr in self._runner.addresses]
        logger.info("ANP 适配器已启动监听 %s", addresses or "unknown")

        # 启动桥接器后台任务
        await self._bridge.start()

        # 标记连接成功
        self._mark_connected()
        return True

    async def disconnect(self) -> None:
        """断开平台连接：停止服务器、桥接任务并标记断开。"""
        # 停止 aiohttp 服务器
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._app = None

        # 停止桥接器
        if self._bridge is not None:
            await self._bridge.stop()
            self._bridge = None

        self._mark_disconnected()

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        """向指定 chat_id 发送消息。

        本适配器仅处理以 "anp:" 为前缀的 chat_id，用于将 Hermes 回复写回 RPC Future。
        当前阶段忽略 reply_to 与 metadata（ANP JSON-RPC 单轮调用无需回复特定消息）。
        """
        if not chat_id.startswith("anp:"):
            return SendResult(success=False, error="unknown chat_id")
        if self._bridge is None:
            return SendResult(success=False, error="adapter not connected")
        rpc_id = chat_id[4:]
        self._bridge.set_result(rpc_id, content)
        return SendResult(success=True, message_id=rpc_id)

    async def get_chat_info(self, chat_id) -> dict[str, Any]:
        """返回 chat 基本信息。"""
        return {
            "chat_id": chat_id,
            "platform": "anp",
        }
