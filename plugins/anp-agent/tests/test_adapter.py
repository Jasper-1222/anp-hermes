"""ANP 平台适配器单元测试。"""

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# 插件目录名包含连字符，加入父目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_gateway_mocks():
    """如果 Hermes 源码未在解释器搜索路径中，则 mock 最小基类与 Platform。"""

    if "gateway.platforms.base" not in sys.modules:
        base_module = ModuleType("gateway.platforms.base")

        class BasePlatformAdapter:
            def __init__(self, config, platform=None):
                self.config = config
                self.platform = platform
                self._message_handler = None
                self._running = False

            @property
            def is_connected(self):
                return self._running

            def set_message_handler(self, handler):
                self._message_handler = handler

            def _mark_connected(self):
                self._running = True

            def _mark_disconnected(self):
                self._running = False

            async def handle_message(self, event):
                if self._message_handler is not None:
                    result = self._message_handler(event)
                    if hasattr(result, "__await__"):
                        await result

        class SendResult:
            def __init__(self, success, message_id=None, error=None, **kwargs):
                self.success = success
                self.message_id = message_id
                self.error = error
                for k, v in kwargs.items():
                    setattr(self, k, v)

        base_module.BasePlatformAdapter = BasePlatformAdapter
        base_module.SendResult = SendResult
        sys.modules["gateway.platforms.base"] = base_module

    if "gateway.config" not in sys.modules:
        config_module = ModuleType("gateway.config")

        class Platform:
            def __init__(self, name):
                self.name = name

            @property
            def value(self):
                return self.name

        config_module.Platform = Platform
        sys.modules["gateway.config"] = config_module


_ensure_gateway_mocks()


from adapter import ANPAdapter
from config import ANPConfig


def _config(data_dir, **kwargs):
    defaults = {
        "host": "127.0.0.1",
        "port": 0,
        "hostname": "localhost",
        "endpoint": "http://localhost:0",
        "data_dir": str(data_dir),
        "request_timeout": 1,
        "future_ttl": 2,
    }
    defaults.update(kwargs)
    return ANPConfig(**defaults)


@pytest.fixture
def platform_config(tmp_path):
    class PlatformConfig:
        extra = {"data_dir": str(tmp_path / "adapter")}

    return PlatformConfig()


@pytest.fixture
def anp_config(tmp_path):
    return _config(tmp_path / "adapter")


@pytest.fixture
def mock_identity(monkeypatch):
    from identity import ANPIdentity

    identity = ANPIdentity(
        did="did:wba:localhost:agent:e1_test",
        did_document={"id": "did:wba:localhost:agent:e1_test"},
        private_key_pem=b"fake-key",
        data_dir=Path("/tmp/anp-test-adapter"),
    )
    monkeypatch.setattr(
        "adapter.load_or_create_identity", lambda data_dir, hostname: identity
    )
    return identity


@pytest.fixture
def mock_auth(monkeypatch):
    from auth import ANPAuth

    auth = MagicMock(spec=ANPAuth)
    monkeypatch.setattr("adapter.create_auth", lambda identity: auth)
    return auth


@pytest.mark.asyncio
async def test_connect_success_sets_connected(
    platform_config, mock_identity, mock_auth
):
    adapter = ANPAdapter(platform_config)
    result = await adapter.connect()
    assert result is True
    assert adapter.is_connected is True
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_disconnect_sets_disconnected(
    platform_config, mock_identity, mock_auth
):
    adapter = ANPAdapter(platform_config)
    await adapter.connect()
    assert adapter.is_connected is True
    await adapter.disconnect()
    assert adapter.is_connected is False


@pytest.mark.asyncio
async def test_send_anp_chat_id_returns_failure_when_not_connected(platform_config):
    adapter = ANPAdapter(platform_config)
    result = await adapter.send("anp:rpc-1", "reply content")
    assert result.success is False
    assert result.error == "adapter not connected"


@pytest.mark.asyncio
async def test_send_anp_chat_id_sets_bridge_result(platform_config):
    adapter = ANPAdapter(platform_config)
    bridge = MagicMock()
    bridge.set_result.return_value = True
    adapter._bridge = bridge

    result = await adapter.send("anp:rpc-1", "reply content")

    bridge.set_result.assert_called_once_with("rpc-1", "reply content")
    assert result.success is True
    assert result.message_id == "rpc-1"


@pytest.mark.asyncio
async def test_send_unknown_chat_id_returns_failure(platform_config):
    adapter = ANPAdapter(platform_config)
    result = await adapter.send("telegram:chat-1", "reply")
    assert result.success is False
    assert result.error == "unknown chat_id"
