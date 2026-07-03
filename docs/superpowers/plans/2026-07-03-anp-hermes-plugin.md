# ANP Hermes 插件实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Hermes 开发一个 ANP 平台插件 `anp-agent`，使 Hermes 智能体能够作为 ANP 服务智能体被其他智能体通过 DID WBA 认证和 JSON-RPC 2.0 调用。

**Architecture:** 插件以 Hermes 平台插件形式运行，内部使用 aiohttp 暴露标准 ANP 端点（`/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`）。收到 `/agent/rpc` 请求后，通过 `asyncio.Future` 桥接到 Hermes 的 `BasePlatformAdapter.handle_message()`，等待 Hermes 通过 `send()` 回调返回结果，再封装为 JSON-RPC 2.0 响应。DID WBA 身份由插件首次启动时自动生成并本地持久化。

**Tech Stack:** Python 3.10+、`anp`（PyPI 0.8.8）、`aiohttp`、Hermes `BasePlatformAdapter`。

## Global Constraints

- 官方语言为**中文**；文档、代码注释、提交信息使用中文。
- 核心插件依赖 `anp>=0.8.8,<0.9.0`，**不**使用 `anp[api]` extras。
- 测试客户端可单独使用 `anp[api]`。
- 使用 ANP 原生 DID WBA（`did:wba:`），不引入 `did:cn`。
- 不依赖 DTR、Portal、Mediator、OpenClaw。
- 不修改 Hermes 核心代码。
- 第一期仅实现身份认证 + JSON-RPC；AP2 支付和 E2EE 延后。
- 仅认证，不授权；任何有效 DID WBA 调用方都可以调用。
- 私钥文件权限 `0o600`。
- 配置优先级：环境变量 > `config.yaml` extra > 默认值。
- 单元测试覆盖率不低于 85%。

---

## File Structure

```
plugins/anp-agent/
├── plugin.yaml          # Hermes 插件清单
├── pyproject.toml       # 依赖：anp, aiohttp；dev: pytest, pytest-asyncio
├── __init__.py          # 导出 register
├── adapter.py           # ANPAdapter（继承 BasePlatformAdapter）
├── bridge.py            # ANPBridge（Future 桥接 + TTL 清理）
├── identity.py          # DID WBA 生成、加载、持久化
├── server.py            # aiohttp 应用和路由处理器
├── constants.py         # 错误码、默认配置值
├── config.py            # 配置加载（env > yaml > default）
└── tests/
    ├── conftest.py
    ├── test_identity.py
    ├── test_bridge.py
    ├── test_server.py
    └── test_integration.py
```

---

## Task 1: 插件骨架与依赖

**Files:**
- Create: `plugins/anp-agent/pyproject.toml`
- Create: `plugins/anp-agent/plugin.yaml`
- Create: `plugins/anp-agent/__init__.py`

**Interfaces:**
- Consumes: 无
- Produces: `plugins/anp-agent` 作为可安装的 Python 包；`register(ctx)` 入口（在 Task 4 实现）。

- [ ] **Step 1: 创建 `pyproject.toml`**

```toml
[project]
name = "hermes-anp-agent"
version = "0.1.0"
description = "Hermes platform plugin for Agent Network Protocol (ANP)"
requires-python = ">=3.10"
dependencies = [
    "anp>=0.8.8,<0.9.0",
    "aiohttp>=3.10.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: 创建 `plugin.yaml`**

```yaml
name: anp-agent
label: ANP Agent
kind: platform
version: 0.1.0
description: >
  Hermes platform plugin that exposes the agent as an ANP service agent
  over DID WBA authenticated JSON-RPC 2.0.
author: anp-hermes
requires_env:
  - name: ANP_ALLOW_ALL_USERS
    description: "Allow any caller during development/testing (set to 1)"
    prompt: "Allow all ANP callers? (1/true for dev)"
    password: false
optional_env:
  - name: ANP_HOST
    description: "Host to bind the ANP HTTP server (default: 0.0.0.0)"
    prompt: "ANP server host"
    password: false
  - name: ANP_PORT
    description: "Port to bind the ANP HTTP server (default: 8900)"
    prompt: "ANP server port"
    password: false
  - name: ANP_HOSTNAME
    description: "Hostname used in generated did:wba (default: localhost)"
    prompt: "ANP DID hostname"
    password: false
  - name: ANP_ENDPOINT
    description: "Public endpoint advertised in ad.json (default: http://{hostname}:{port})"
    prompt: "ANP public endpoint"
    password: false
  - name: ANP_DATA_DIR
    description: "Directory to store DID documents and private keys (default: ~/.hermes/plugins/anp-agent/)"
    prompt: "ANP data directory"
    password: false
  - name: ANP_REQUEST_TIMEOUT
    description: "Max seconds to wait for Hermes reply (default: 300)"
    prompt: "ANP request timeout"
    password: false
  - name: ANP_FUTURE_TTL
    description: "Max seconds to keep pending futures before cleanup (default: 300)"
    prompt: "ANP future TTL"
    password: false
```

- [ ] **Step 3: 创建 `__init__.py`**

```python
"""Hermes ANP platform plugin."""

from .adapter import register

__all__ = ["register"]
```

- [ ] **Step 4: 安装插件到开发环境**

```bash
cd /home/peter/anp-hermes
python -m pip install -e "plugins/anp-agent[dev]"
```

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/
git commit -m "chore: scaffold anp-agent plugin package"
```

---

## Task 2: 配置加载模块

**Files:**
- Create: `plugins/anp-agent/config.py`
- Create: `plugins/anp-agent/constants.py`
- Test: `plugins/anp-agent/tests/test_config.py`

**Interfaces:**
- Consumes: `PlatformConfig` from Hermes（可选，不直接 import，使用 dict-like 访问）
- Produces: `ANPConfig` dataclass with `host`, `port`, `hostname`, `endpoint`, `data_dir`, `request_timeout`, `future_ttl`.

- [ ] **Step 1: 编写失败测试**

Create `plugins/anp-agent/tests/test_config.py`:

```python
import os
from pathlib import Path

import pytest

from anp_agent.config import ANPConfig, load_config


class FakePlatformConfig:
    def __init__(self, extra=None):
        self.extra = extra or {}


def test_defaults():
    cfg = load_config(FakePlatformConfig())
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8900
    assert cfg.hostname == "localhost"
    assert cfg.data_dir == Path.home() / ".hermes" / "plugins" / "anp-agent"
    assert cfg.request_timeout == 300
    assert cfg.future_ttl == 300


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("ANP_HOST", "127.0.0.1")
    monkeypatch.setenv("ANP_PORT", "9000")
    monkeypatch.setenv("ANP_HOSTNAME", "example.com")
    monkeypatch.setenv("ANP_ENDPOINT", "https://example.com/agent")
    monkeypatch.setenv("ANP_REQUEST_TIMEOUT", "60")
    monkeypatch.setenv("ANP_FUTURE_TTL", "120")
    cfg = load_config(FakePlatformConfig())
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.hostname == "example.com"
    assert cfg.endpoint == "https://example.com/agent"
    assert cfg.request_timeout == 60
    assert cfg.future_ttl == 120


def test_extra_overrides_default():
    cfg = load_config(FakePlatformConfig({"port": 8800, "hostname": "agent.example.com"}))
    assert cfg.port == 8800
    assert cfg.hostname == "agent.example.com"


def test_env_beats_extra(monkeypatch):
    monkeypatch.setenv("ANP_PORT", "7777")
    cfg = load_config(FakePlatformConfig({"port": 8800}))
    assert cfg.port == 7777
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/peter/anp-hermes
pytest plugins/anp-agent/tests/test_config.py -v
```

Expected: 失败，模块未找到。

- [ ] **Step 3: 实现 `constants.py` 和 `config.py`**

Create `plugins/anp-agent/constants.py`:

```python
"""Shared constants for the ANP Hermes plugin."""

from pathlib import Path

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8900
DEFAULT_HOSTNAME = "localhost"
DEFAULT_REQUEST_TIMEOUT = 300
DEFAULT_FUTURE_TTL = 300

DEFAULT_DATA_DIR = Path.home() / ".hermes" / "plugins" / "anp-agent"
```

Create `plugins/anp-agent/config.py`:

```python
"""Configuration loading for the ANP Hermes plugin."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_DATA_DIR,
    DEFAULT_FUTURE_TTL,
    DEFAULT_HOST,
    DEFAULT_HOSTNAME,
    DEFAULT_PORT,
    DEFAULT_REQUEST_TIMEOUT,
)


@dataclass(frozen=True)
class ANPConfig:
    host: str
    port: int
    hostname: str
    endpoint: str
    data_dir: Path
    request_timeout: int
    future_ttl: int


def _get_str(extra: dict, env_name: str, default: str) -> str:
    return os.environ.get(env_name) or extra.get(env_name.lower().replace("ANP_", ""), default) or default


def _get_int(extra: dict, env_name: str, default: int) -> int:
    raw = os.environ.get(env_name)
    if raw is None:
        raw = extra.get(env_name.lower().replace("ANP_", ""))
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _get_path(extra: dict, env_name: str, default: Path) -> Path:
    raw = os.environ.get(env_name) or extra.get(env_name.lower().replace("ANP_", ""))
    if raw:
        return Path(raw).expanduser()
    return default


def load_config(platform_config: Any) -> ANPConfig:
    """Load configuration with env > config.yaml extra > default."""
    extra = getattr(platform_config, "extra", None) or {}

    host = _get_str(extra, "ANP_HOST", DEFAULT_HOST)
    port = _get_int(extra, "ANP_PORT", DEFAULT_PORT)
    hostname = _get_str(extra, "ANP_HOSTNAME", DEFAULT_HOSTNAME)
    data_dir = _get_path(extra, "ANP_DATA_DIR", DEFAULT_DATA_DIR)
    request_timeout = _get_int(extra, "ANP_REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT)
    future_ttl = _get_int(extra, "ANP_FUTURE_TTL", DEFAULT_FUTURE_TTL)

    endpoint = os.environ.get("ANP_ENDPOINT") or extra.get("endpoint")
    if not endpoint:
        endpoint = f"http://{hostname}:{port}"

    return ANPConfig(
        host=host,
        port=port,
        hostname=hostname,
        endpoint=endpoint,
        data_dir=data_dir,
        request_timeout=request_timeout,
        future_ttl=future_ttl,
    )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_config.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/config.py plugins/anp-agent/constants.py plugins/anp-agent/tests/test_config.py
git commit -m "feat: add ANP plugin configuration loader"
```

---

## Task 3: DID WBA 身份管理

**Files:**
- Create: `plugins/anp-agent/identity.py`
- Test: `plugins/anp-agent/tests/test_identity.py`

**Interfaces:**
- Consumes: `ANPConfig`（用于 `data_dir` 和 `hostname`）
- Produces: `IdentityManager` 类，提供 `ensure_identity() -> Identity`；`Identity` dataclass 含 `did`, `did_document`, `private_key_path`。

- [ ] **Step 1: 编写失败测试**

Create `plugins/anp-agent/tests/test_identity.py`:

```python
import json
import stat
from pathlib import Path

import pytest

from anp_agent.identity import IdentityManager, load_identity
from anp_agent.config import ANPConfig


def _config(tmp_path: Path) -> ANPConfig:
    return ANPConfig(
        host="0.0.0.0",
        port=8900,
        hostname="test.agent-network",
        endpoint="http://test.agent-network:8900",
        data_dir=tmp_path,
        request_timeout=300,
        future_ttl=300,
    )


def test_generates_identity_on_first_run(tmp_path):
    cfg = _config(tmp_path)
    mgr = IdentityManager(cfg)
    identity = mgr.ensure_identity()
    assert identity.did.startswith("did:wba:")
    assert identity.did_document_path.exists()
    assert identity.private_key_path.exists()
    assert (tmp_path / "agent.json").exists()
    mode = stat.S_IMODE(identity.private_key_path.stat().st_mode)
    assert mode == 0o600


def test_loads_existing_identity(tmp_path):
    cfg = _config(tmp_path)
    mgr = IdentityManager(cfg)
    first = mgr.ensure_identity()
    second = load_identity(cfg)
    assert second.did == first.did


def test_agent_json_contains_expected_fields(tmp_path):
    cfg = _config(tmp_path)
    mgr = IdentityManager(cfg)
    mgr.ensure_identity()
    data = json.loads((tmp_path / "agent.json").read_text(encoding="utf-8"))
    assert "did" in data
    assert "hostname" in data
    assert data["hostname"] == "test.agent-network"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest plugins/anp-agent/tests/test_identity.py -v
```

Expected: 失败。

- [ ] **Step 3: 实现 `identity.py`**

Create `plugins/anp-agent/identity.py`:

```python
"""DID WBA identity generation and persistence for the ANP Hermes plugin."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from anp.authentication import create_did_wba_document

from .config import ANPConfig


@dataclass(frozen=True)
class Identity:
    did: str
    did_document: dict
    did_document_path: Path
    private_key_path: Path


class IdentityManager:
    """Generates or loads a DID WBA identity for the ANP service agent."""

    def __init__(self, config: ANPConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.did_document_path = self.data_dir / "did.json"
        self.private_key_path = self.data_dir / "private_key.pem"
        self.agent_json_path = self.data_dir / "agent.json"

    def ensure_identity(self) -> Identity:
        if self._has_existing_identity():
            return self._load()
        return self._generate()

    def _has_existing_identity(self) -> bool:
        return (
            self.did_document_path.exists()
            and self.private_key_path.exists()
            and self.agent_json_path.exists()
        )

    def _load(self) -> Identity:
        did_document = json.loads(self.did_document_path.read_text(encoding="utf-8"))
        return Identity(
            did=did_document["id"],
            did_document=did_document,
            did_document_path=self.did_document_path,
            private_key_path=self.private_key_path,
        )

    def _generate(self) -> Identity:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        did_document, keys = create_did_wba_document(
            hostname=self.config.hostname,
            path_segments=["agent"],
            agent_description_url=f"{self.config.endpoint}/ad.json",
            did_profile="e1",
        )

        # keys is dict[fragment, (private_bytes, public_bytes)]
        auth_key = keys.get("auth")
        if auth_key is None:
            auth_key = next(iter(keys.values()))
        private_bytes, _public_bytes = auth_key

        self.did_document_path.write_text(
            json.dumps(did_document, indent=2), encoding="utf-8"
        )
        self.private_key_path.write_bytes(private_bytes)
        os.chmod(self.private_key_path, 0o600)

        agent_meta = {
            "did": did_document["id"],
            "hostname": self.config.hostname,
            "endpoint": self.config.endpoint,
        }
        self.agent_json_path.write_text(
            json.dumps(agent_meta, indent=2), encoding="utf-8"
        )

        return Identity(
            did=did_document["id"],
            did_document=did_document,
            did_document_path=self.did_document_path,
            private_key_path=self.private_key_path,
        )


def load_identity(config: ANPConfig) -> Identity:
    """Convenience wrapper to load an existing identity."""
    mgr = IdentityManager(config)
    return mgr.ensure_identity()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_identity.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/identity.py plugins/anp-agent/tests/test_identity.py
git commit -m "feat: add DID WBA identity management"
```

---

## Task 4: Future 桥接模块

**Files:**
- Create: `plugins/anp-agent/bridge.py`
- Test: `plugins/anp-agent/tests/test_bridge.py`

**Interfaces:**
- Consumes: `ANPConfig`（`request_timeout`, `future_ttl`）
- Produces: `ANPBridge` 类，提供 `call(rpc_id, method, params, caller_did) -> dict`；`set_result(rpc_id, result)`；`cancel_all()`。

- [ ] **Step 1: 编写失败测试**

Create `plugins/anp-agent/tests/test_bridge.py`:

```python
import asyncio

import pytest

from anp_agent.bridge import ANPBridge
from anp_agent.config import ANPConfig


def _config():
    return ANPConfig(
        host="0.0.0.0",
        port=8900,
        hostname="localhost",
        endpoint="http://localhost:8900",
        data_dir="/tmp/anp-test",
        request_timeout=1,
        future_ttl=2,
    )


class FakeAdapter:
    def __init__(self):
        self.events = []

    async def handle_message(self, event):
        self.events.append(event)

    def build_source(self, **kwargs):
        class Source:
            def __init__(self, **kw):
                self.__dict__.update(kw)
        return Source(**kwargs)


@pytest.mark.asyncio
async def test_call_returns_result():
    adapter = FakeAdapter()
    bridge = ANPBridge(adapter, _config())

    async def delayed_reply():
        await asyncio.sleep(0.1)
        bridge.set_result("rpc-1", "hello")

    asyncio.create_task(delayed_reply())
    result = await bridge.call("rpc-1", "chat", {"message": "hi"}, "did:wba:alice")
    assert result == {"jsonrpc": "2.0", "result": "hello", "id": "rpc-1"}


@pytest.mark.asyncio
async def test_call_times_out():
    adapter = FakeAdapter()
    bridge = ANPBridge(adapter, _config())
    result = await bridge.call("rpc-2", "chat", {"message": "hi"}, "did:wba:alice")
    assert result["error"]["code"] == -32603
    assert "timeout" in result["error"]["message"].lower()


@pytest.mark.asyncio
async def test_duplicate_rpc_id_rejected():
    adapter = FakeAdapter()
    bridge = ANPBridge(adapter, _config())
    first = asyncio.create_task(bridge.call("rpc-3", "chat", {}, "did:wba:alice"))
    await asyncio.sleep(0.05)
    second = await bridge.call("rpc-3", "chat", {}, "did:wba:alice")
    assert second["error"]["code"] == -32600
    bridge.set_result("rpc-3", "done")
    await first
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest plugins/anp-agent/tests/test_bridge.py -v
```

Expected: 失败。

- [ ] **Step 3: 实现 `bridge.py`**

Create `plugins/anp-agent/bridge.py`:

```python
"""Bridge ANP JSON-RPC requests to Hermes MessageEvents via asyncio.Future."""

import asyncio
import json
import time
from typing import Any, Dict, Optional

from .config import ANPConfig


class ANPBridge:
    """Waits for Hermes replies and returns them as JSON-RPC responses."""

    def __init__(self, adapter, config: ANPConfig):
        self.adapter = adapter
        self.config = config
        self._pending: Dict[str, asyncio.Future] = {}
        self._created_at: Dict[str, float] = {}

    def _cleanup_expired(self) -> None:
        now = time.monotonic()
        cutoff = now - self.config.future_ttl
        expired = [rpc_id for rpc_id, created in self._created_at.items() if created < cutoff]
        for rpc_id in expired:
            future = self._pending.pop(rpc_id, None)
            if future and not future.done():
                future.set_exception(asyncio.TimeoutError("future expired before completion"))
            self._created_at.pop(rpc_id, None)

    async def call(self, rpc_id: str, method: str, params: dict, caller_did: str) -> dict:
        self._cleanup_expired()

        if rpc_id in self._pending:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": f"duplicate rpc_id: {rpc_id}"},
                "id": rpc_id,
            }

        try:
            from gateway.platforms.base import MessageEvent, MessageType
        except ImportError:
            # Fallback for standalone tests without Hermes
            MessageEvent = _MockMessageEvent
            MessageType = _MockMessageType()

        future = asyncio.get_event_loop().create_future()
        self._pending[rpc_id] = future
        self._created_at[rpc_id] = time.monotonic()

        event = MessageEvent(
            text=f"ANP 调用: {method}\n参数: {json.dumps(params, ensure_ascii=False)}",
            message_type=MessageType.TEXT,
            source=self.adapter.build_source(
                chat_id=f"anp:{rpc_id}",
                user_id=caller_did,
                user_name=caller_did,
                chat_type="dm",
            ),
            raw_message={"method": method, "params": params, "id": rpc_id},
        )

        await self.adapter.handle_message(event)

        try:
            result = await asyncio.wait_for(future, timeout=self.config.request_timeout)
            return {"jsonrpc": "2.0", "result": result, "id": rpc_id}
        except asyncio.TimeoutError:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "处理超时"},
                "id": rpc_id,
            }
        finally:
            self._pending.pop(rpc_id, None)
            self._created_at.pop(rpc_id, None)

    def set_result(self, rpc_id: str, result: Any) -> None:
        future = self._pending.pop(rpc_id, None)
        if future:
            self._created_at.pop(rpc_id, None)
            if not future.done():
                future.set_result(result)

    def cancel_all(self) -> None:
        for rpc_id, future in list(self._pending.items()):
            if not future.done():
                future.cancel()
        self._pending.clear()
        self._created_at.clear()


class _MockMessageType:
    TEXT = "text"


class _MockMessageEvent:
    def __init__(self, text, message_type, source, raw_message=None):
        self.text = text
        self.message_type = message_type
        self.source = source
        self.raw_message = raw_message
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_bridge.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/bridge.py plugins/anp-agent/tests/test_bridge.py
git commit -m "feat: add ANP-to-Hermes Future bridge"
```

---

## Task 5: ANP HTTP 服务端

**Files:**
- Create: `plugins/anp-agent/server.py`
- Test: `plugins/anp-agent/tests/test_server.py`

**Interfaces:**
- Consumes: `ANPConfig`, `Identity`, `ANPBridge`
- Produces: `create_app(identity, bridge) -> aiohttp.web.Application`；`ANPServer` 启动/停止封装。

- [ ] **Step 1: 编写失败测试**

Create `plugins/anp-agent/tests/test_server.py`:

```python
import json

import pytest
from aiohttp import web

from anp_agent.bridge import ANPBridge
from anp_agent.config import ANPConfig
from anp_agent.server import create_app


def _identity(tmp_path):
    from anp_agent.identity import IdentityManager
    cfg = ANPConfig(
        host="127.0.0.1",
        port=8901,
        hostname="test.agent-network",
        endpoint="http://test.agent-network:8901",
        data_dir=tmp_path,
        request_timeout=1,
        future_ttl=2,
    )
    return IdentityManager(cfg).ensure_identity(), cfg


class FakeAdapter:
    def __init__(self):
        self.events = []

    async def handle_message(self, event):
        self.events.append(event)

    def build_source(self, **kwargs):
        class Source:
            def __init__(self, **kw):
                self.__dict__.update(kw)
        return Source(**kwargs)


@pytest.mark.asyncio
async def test_ad_json(aiohttp_client, tmp_path):
    identity, cfg = _identity(tmp_path)
    bridge = ANPBridge(FakeAdapter(), cfg)
    app = create_app(identity, bridge, cfg)
    client = await aiohttp_client(app)
    resp = await client.get("/agent/ad.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["did"] == identity.did


@pytest.mark.asyncio
async def test_interface_json(aiohttp_client, tmp_path):
    identity, cfg = _identity(tmp_path)
    bridge = ANPBridge(FakeAdapter(), cfg)
    app = create_app(identity, bridge, cfg)
    client = await aiohttp_client(app)
    resp = await client.get("/agent/interface.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["openrpc"] == "1.2.6"
    assert any(m["name"] == "chat" for m in data["methods"])


@pytest.mark.asyncio
async def test_rpc_missing_signature(aiohttp_client, tmp_path):
    identity, cfg = _identity(tmp_path)
    bridge = ANPBridge(FakeAdapter(), cfg)
    app = create_app(identity, bridge, cfg)
    client = await aiohttp_client(app)
    resp = await client.post("/agent/rpc", data=json.dumps({
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "hi"},
        "id": "1",
    }), headers={"Content-Type": "application/json"})
    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32001
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest plugins/anp-agent/tests/test_server.py -v
```

Expected: 失败。

- [ ] **Step 3: 实现 `server.py`**

Create `plugins/anp-agent/server.py`:

```python
"""aiohttp server exposing ANP endpoints."""

import json
import logging
from typing import Any

from aiohttp import web

from .bridge import ANPBridge
from .config import ANPConfig
from .identity import Identity

logger = logging.getLogger(__name__)


def _json_rpc_error(rpc_id: Any, code: int, message: str, status: int = 200):
    body = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": rpc_id}
    return web.json_response(body, status=status)


def create_app(identity: Identity, bridge: ANPBridge, config: ANPConfig) -> web.Application:
    app = web.Application()
    app["identity"] = identity
    app["bridge"] = bridge
    app["config"] = config

    app.router.add_get("/agent/ad.json", _handle_ad_json)
    app.router.add_get("/agent/interface.json", _handle_interface_json)
    app.router.add_post("/agent/rpc", _handle_rpc)
    return app


async def _handle_ad_json(request: web.Request) -> web.Response:
    identity = request.app["identity"]
    config = request.app["config"]
    ad = {
        "@context": "https://agent-network-protocol.com/context/v1",
        "type": "AgentDescription",
        "name": "Hermes ANP Agent",
        "description": "Hermes agent exposed over ANP",
        "did": identity.did,
        "version": "0.1.0",
        "entryPoint": config.endpoint,
        "interfaceUrl": f"{config.endpoint}/interface.json",
        "rpcEndpoint": f"{config.endpoint}/rpc",
    }
    return web.json_response(ad)


async def _handle_interface_json(request: web.Request) -> web.Response:
    interface = {
        "openrpc": "1.2.6",
        "info": {
            "title": "Hermes ANP Agent Interface",
            "version": "0.1.0",
        },
        "methods": [
            {
                "name": "chat",
                "summary": "Send a message to the Hermes agent",
                "params": [
                    {
                        "name": "message",
                        "schema": {"type": "string"},
                        "required": True,
                    }
                ],
                "result": {
                    "name": "response",
                    "schema": {"type": "string"},
                },
            }
        ],
    }
    return web.json_response(interface)


async def _handle_rpc(request: web.Request) -> web.Response:
    bridge = request.app["bridge"]

    try:
        body = await request.read()
        payload = json.loads(body)
    except json.JSONDecodeError:
        return _json_rpc_error(None, -32700, "无效的 JSON", status=400)

    rpc_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if not isinstance(method, str):
        return _json_rpc_error(rpc_id, -32600, "缺少或无效的 method", status=400)

    # Authentication placeholder: validate DID WBA signature
    auth_ok, auth_reason = await _verify_signature(request, body)
    if not auth_ok:
        return _json_rpc_error(rpc_id, -32001, f"身份验证失败: {auth_reason}", status=401)

    caller_did = request.get("caller_did", "")
    response = await bridge.call(str(rpc_id), method, params, caller_did)
    return web.json_response(response)


async def _verify_signature(request: web.Request, body: bytes) -> tuple[bool, str]:
    """Placeholder for DID WBA signature verification.

    Task 6 replaces this with real `DidWbaVerifier` logic.
    """
    signature_input = request.headers.get("Signature-Input")
    if not signature_input:
        return False, "缺少 Signature-Input header"
    # Minimal placeholder: accept any non-empty signature input in tests.
    request["caller_did"] = "did:wba:placeholder.example.com:placeholder"
    return True, ""
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_server.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/server.py plugins/anp-agent/tests/test_server.py
git commit -m "feat: add ANP HTTP server endpoints"
```

---

## Task 6: DID WBA 签名验证

**Files:**
- Modify: `plugins/anp-agent/server.py`（替换 `_verify_signature`）
- Test: `plugins/anp-agent/tests/test_server.py`（补充合法签名测试）

**Interfaces:**
- Consumes: `anp.authentication.did_wba_verifier`
- Produces: `_verify_signature` 返回 `(ok, reason)` 并设置 `request["caller_did"]`。

- [ ] **Step 1: 编写失败测试**

Add to `plugins/anp-agent/tests/test_server.py`:

```python
import asyncio
from pathlib import Path

import pytest
from anp.authentication import DIDWbaAuthHeader, create_did_wba_document


@pytest.fixture
def caller_credentials(tmp_path):
    did_doc, keys = create_did_wba_document(
        hostname="caller.example.com",
        path_segments=["user"],
        agent_description_url="https://caller.example.com/ad.json",
        did_profile="e1",
    )
    did_path = tmp_path / "caller_did.json"
    key_path = tmp_path / "caller_private.pem"
    did_path.write_text(json.dumps(did_doc), encoding="utf-8")
    auth_key = keys.get("auth") or next(iter(keys.values()))
    key_path.write_bytes(auth_key[0])
    return str(did_path), str(key_path), did_doc["id"]


@pytest.mark.asyncio
async def test_rpc_with_valid_signature(aiohttp_client, tmp_path, caller_credentials):
    from anp_agent.identity import IdentityManager
    cfg = ANPConfig(
        host="127.0.0.1",
        port=8902,
        hostname="service.example.com",
        endpoint="http://service.example.com:8902",
        data_dir=tmp_path / "service",
        request_timeout=1,
        future_ttl=2,
    )
    identity = IdentityManager(cfg).ensure_identity()

    class ReplyingAdapter:
        def __init__(self):
            self.bridge = None

        async def handle_message(self, event):
            asyncio.get_event_loop().call_later(0.05, self._reply, event.source.chat_id)

        def _reply(self, chat_id):
            rpc_id = chat_id.split(":", 1)[1]
            self.bridge.set_result(rpc_id, "pong")

        def build_source(self, **kwargs):
            class Source:
                def __init__(self, **kw):
                    self.__dict__.update(kw)
            return Source(**kwargs)

    bridge = ANPBridge(ReplyingAdapter(), cfg)
    ReplyingAdapter().bridge = bridge
    app = create_app(identity, bridge, cfg)
    client = await aiohttp_client(app)

    did_path, key_path, caller_did = caller_credentials
    auth = DIDWbaAuthHeader(did_document_path=did_path, private_key_path=key_path)
    url = "http://127.0.0.1/agent/rpc"
    headers = auth.get_auth_header(url, force_new=True)
    headers["Content-Type"] = "application/json"

    resp = await client.post("/agent/rpc", data=json.dumps({
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "ping"},
        "id": "42",
    }), headers=headers)

    assert resp.status == 200
    data = await resp.json()
    assert data["result"] == "pong"
    assert data["id"] == "42"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest plugins/anp-agent/tests/test_server.py::test_rpc_with_valid_signature -v
```

Expected: 失败，因为 `_verify_signature` 是 placeholder。

- [ ] **Step 3: 实现真实签名验证**

Replace `_verify_signature` in `plugins/anp-agent/server.py`:

```python
async def _verify_signature(request: web.Request, body: bytes) -> tuple[bool, str]:
    try:
        from anp.authentication.did_wba_verifier import DidWbaVerifier, DidWbaVerifierConfig
        from anp.authentication import http_signatures
    except ImportError as e:
        return False, f"缺少 ANP 认证依赖: {e}"

    headers = dict(request.headers)
    keyid = http_signatures.extract_keyid_from_headers(headers)
    if not keyid:
        return False, "缺少 Signature-Input 或 keyid"

    if "#" not in keyid:
        return False, "无效的 keyid 格式"

    caller_did = keyid.rsplit("#", 1)[0]

    # Resolve DID document via HTTP(S) fetch
    did_doc_url = f"{caller_did}/did.json"
    if did_doc_url.startswith("did:wba:"):
        did_doc_url = did_doc_url.replace("did:wba:", "https://", 1)

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(did_doc_url) as resp:
                if resp.status != 200:
                    return False, f"无法解析 DID 文档: {resp.status}"
                caller_doc = await resp.json()
    except Exception as e:
        return False, f"解析 DID 文档失败: {e}"

    # Verify signature using ANP verifier
    try:
        verifier = DidWbaVerifier(
            DidWbaVerifierConfig(
                jwt_private_key="",
                jwt_public_key="",
                jwt_algorithm="RS256",
                access_token_expire_minutes=5,
            )
        )
        result = await verifier.verify_request(
            method=request.method,
            url=str(request.url),
            headers=headers,
            body=body,
            domain=request.url.host,
        )
        request["caller_did"] = result.get("did", caller_did)
        return True, ""
    except Exception as e:
        return False, f"签名验证失败: {e}"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_server.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/server.py plugins/anp-agent/tests/test_server.py
git commit -m "feat: add DID WBA signature verification"
```

---

## Task 7: Hermes 平台适配器

**Files:**
- Create: `plugins/anp-agent/adapter.py`
- Modify: `plugins/anp-agent/__init__.py`（导出 `register`）
- Test: `plugins/anp-agent/tests/test_adapter.py`

**Interfaces:**
- Consumes: `BasePlatformAdapter`, `ANPConfig`, `IdentityManager`, `ANPBridge`, `create_app`
- Produces: `ANPAdapter` 类 + `register(ctx)` 入口。

- [ ] **Step 1: 编写失败测试**

Create `plugins/anp-agent/tests/test_adapter.py`:

```python
import pytest

from anp_agent.adapter import ANPAdapter
from anp_agent.config import ANPConfig


def _config(tmp_path):
    return ANPConfig(
        host="127.0.0.1",
        port=0,
        hostname="test.agent-network",
        endpoint="http://test.agent-network:8900",
        data_dir=tmp_path,
        request_timeout=1,
        future_ttl=2,
    )


class FakePlatform:
    value = "anp"


class FakePlatformConfig:
    def __init__(self, tmp_path):
        self.extra = {}
        self.data_dir = tmp_path


@pytest.mark.asyncio
async def test_adapter_connect_and_disconnect(tmp_path):
    from unittest.mock import AsyncMock
    config = FakePlatformConfig(tmp_path)
    adapter = ANPAdapter(config)
    adapter.handle_message = AsyncMock()
    ok = await adapter.connect()
    assert ok is True
    assert adapter.is_connected
    await adapter.disconnect()
    assert not adapter.is_connected
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest plugins/anp-agent/tests/test_adapter.py -v
```

Expected: 失败。

- [ ] **Step 3: 实现 `adapter.py`**

Create `plugins/anp-agent/adapter.py`:

```python
"""Hermes BasePlatformAdapter for ANP."""

import logging
from pathlib import Path
from typing import Any, Dict

from aiohttp import web

from .bridge import ANPBridge
from .config import ANPConfig, load_config
from .identity import IdentityManager
from .server import create_app

try:
    from gateway.config import Platform, PlatformConfig
    from gateway.platforms.base import (
        BasePlatformAdapter,
        MessageEvent,
        MessageType,
        SendResult,
    )
    _HERMES_AVAILABLE = True
except ImportError:
    _HERMES_AVAILABLE = False

    class Platform:
        def __init__(self, name):
            self.value = name

    class PlatformConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.extra = kwargs.get("extra", {})

    class BasePlatformAdapter:
        def __init__(self, config, platform):
            self.config = config
            self.platform = platform
            self._connected = False

        def _mark_connected(self):
            self._connected = True

        def _mark_disconnected(self):
            self._connected = False

        @property
        def is_connected(self):
            return self._connected

        def build_source(self, **kwargs):
            class _Source:
                def __init__(self, **kw):
                    self.__dict__.update(kw)
            return _Source(**kwargs)

        async def handle_message(self, event):
            pass

    class MessageEvent:
        def __init__(self, text="", message_type=None, source=None, raw_message=None):
            self.text = text
            self.message_type = message_type
            self.source = source
            self.raw_message = raw_message

    class MessageType:
        TEXT = "text"

    class SendResult:
        def __init__(self, success=True, message_id="", error=""):
            self.success = success
            self.message_id = message_id
            self.error = error


logger = logging.getLogger(__name__)


class ANPAdapter(BasePlatformAdapter):
    """Hermes platform adapter exposing the agent over ANP."""

    def __init__(self, config: PlatformConfig):
        platform = Platform("anp")
        super().__init__(config=config, platform=platform)
        self.anp_config = load_config(config)
        self.identity_manager = IdentityManager(self.anp_config)
        self._identity = None
        self._bridge = None
        self._runner = None

    @property
    def name(self) -> str:
        return "ANP"

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        try:
            self._identity = self.identity_manager.ensure_identity()
            self._bridge = ANPBridge(self, self.anp_config)
            app = create_app(self._identity, self._bridge, self.anp_config)
            self._runner = web.AppRunner(app)
            await self._runner.setup()
            site = web.TCPSite(self._runner, self.anp_config.host, self.anp_config.port)
            await site.start()
            logger.info("ANP plugin listening on %s:%s", self.anp_config.host, self.anp_config.port)
            self._mark_connected()
            return True
        except Exception as e:
            logger.exception("ANP plugin connect failed: %s", e)
            self._set_fatal_error("connect_failed", str(e), retryable=True)
            return False

    async def disconnect(self) -> None:
        if self._bridge:
            self._bridge.cancel_all()
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._mark_disconnected()

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to=None,
        metadata=None,
    ) -> SendResult:
        if chat_id.startswith("anp:") and self._bridge:
            rpc_id = chat_id.split(":", 1)[1]
            self._bridge.set_result(rpc_id, content)
            return SendResult(success=True, message_id=rpc_id)
        return SendResult(success=True, message_id="dummy")

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        return {"name": chat_id, "type": "dm"}

    def _set_fatal_error(self, code, message, retryable=True):
        # Mirror base method when available; harmless otherwise.
        if hasattr(super(), "_set_fatal_error"):
            super()._set_fatal_error(code, message, retryable)


def check_requirements() -> bool:
    try:
        import aiohttp  # noqa: F401
        import anp  # noqa: F401
        return True
    except ImportError:
        return False


def validate_config(config) -> bool:
    try:
        cfg = load_config(config)
        return cfg.port > 0
    except Exception:
        return False


def is_connected(config) -> bool:
    return True


def register(ctx) -> None:
    ctx.register_platform(
        name="anp",
        label="ANP Agent",
        adapter_factory=lambda cfg: ANPAdapter(cfg),
        check_fn=check_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        required_env=["ANP_ALLOW_ALL_USERS"],
        install_hint="pip install anp aiohttp",
        max_message_length=4000,
        emoji="🌐",
        platform_hint="你是一个通过 ANP 协议被其他智能体调用的 Hermes 服务智能体。",
        allowed_users_env="ANP_ALLOWED_USERS",
        allow_all_env="ANP_ALLOW_ALL_USERS",
    )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_adapter.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/adapter.py plugins/anp-agent/__init__.py plugins/anp-agent/tests/test_adapter.py
git commit -m "feat: add Hermes ANP platform adapter"
```

---

## Task 8: 集成测试与 README

**Files:**
- Create: `plugins/anp-agent/tests/test_integration.py`
- Create: `plugins/anp-agent/README.md`
- Modify: `/home/peter/anp-hermes/CLAUDE.md`（补充 ANP 插件开发命令）

- [ ] **Step 1: 编写集成测试**

Create `plugins/anp-agent/tests/test_integration.py`:

```python
import asyncio
import json
from pathlib import Path

import pytest
from aiohttp import web

from anp_agent.adapter import ANPAdapter
from anp_agent.bridge import ANPBridge
from anp_agent.config import ANPConfig
from anp_agent.identity import IdentityManager
from anp_agent.server import create_app


async def _discover_and_chat(tmp_path: Path):
    cfg = ANPConfig(
        host="127.0.0.1",
        port=8903,
        hostname="svc.example.com",
        endpoint="http://svc.example.com:8903",
        data_dir=tmp_path / "svc",
        request_timeout=2,
        future_ttl=5,
    )
    identity = IdentityManager(cfg).ensure_identity()

    class EchoAdapter:
        def __init__(self):
            self.bridge = None

        async def handle_message(self, event):
            text = event.raw_message["params"].get("message", "")
            rpc_id = event.source.chat_id.split(":", 1)[1]
            asyncio.get_event_loop().call_later(0.05, self._reply, rpc_id, f"echo: {text}")

        def _reply(self, rpc_id, text):
            self.bridge.set_result(rpc_id, text)

        def build_source(self, **kwargs):
            class Source:
                def __init__(self, **kw):
                    self.__dict__.update(kw)
            return Source(**kwargs)

    bridge = ANPBridge(EchoAdapter(), cfg)
    EchoAdapter().bridge = bridge
    app = create_app(identity, bridge, cfg)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, cfg.host, cfg.port)
    await site.start()

    try:
        from anp.openanp import RemoteAgent
        from anp.authentication import DIDWbaAuthHeader

        client_did_path = tmp_path / "client_did.json"
        client_key_path = tmp_path / "client_private.pem"
        from anp.authentication import create_did_wba_document
        did_doc, keys = create_did_wba_document(
            hostname="client.example.com",
            path_segments=["u"],
            agent_description_url="https://client.example.com/ad.json",
        )
        client_did_path.write_text(json.dumps(did_doc), encoding="utf-8")
        client_key_path.write_bytes((keys.get("auth") or next(iter(keys.values())))[0])

        auth = DIDWbaAuthHeader(
            did_document_path=str(client_did_path),
            private_key_path=str(client_key_path),
        )
        agent = await RemoteAgent.discover(f"http://127.0.0.1:{cfg.port}/agent/ad.json", auth)
        result = await agent.chat(message="hello")
        assert result == "echo: hello"
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_integration(tmp_path):
    await _discover_and_chat(tmp_path)
```

- [ ] **Step 2: 运行测试确认通过**

```bash
pytest plugins/anp-agent/tests/test_integration.py -v
```

Expected: PASS（可能需要安装 `anp[api]`）。

- [ ] **Step 3: 编写 `README.md`**

Create `plugins/anp-agent/README.md`:

```markdown
# Hermes ANP Agent Plugin

让 Hermes 智能体作为 ANP 服务智能体运行。

## 安装

```bash
pip install -e "plugins/anp-agent[dev]"
```

将插件复制到 Hermes 插件目录：

```bash
ln -s /path/to/anp-hermes/plugins/anp-agent ~/.hermes/plugins/anp-agent
```

## 配置

在 `~/.hermes/config.yaml` 中启用：

```yaml
gateway:
  platforms:
    anp:
      enabled: true
      extra:
        host: 0.0.0.0
        port: 8900
        hostname: your-hostname.example.com
        endpoint: https://your-hostname.example.com:8900
```

或使用环境变量：

```bash
export ANP_HOST=0.0.0.0
export ANP_PORT=8900
export ANP_HOSTNAME=your-hostname.example.com
export ANP_ENDPOINT=https://your-hostname.example.com:8900
export ANP_ALLOW_ALL_USERS=1
```

## 测试

```bash
pytest plugins/anp-agent/tests -v
```

## 调用

使用 ANP demo 客户端：

```python
from anp.openanp import RemoteAgent
from anp.authentication import DIDWbaAuthHeader

auth = DIDWbaAuthHeader(did_document_path="...", private_key_path="...")
agent = await RemoteAgent.discover("https://your-hostname.example.com:8900/agent/ad.json", auth)
result = await agent.chat(message="你好")
print(result)
```
```

- [ ] **Step 4: 更新根目录 `CLAUDE.md`**

Add under `## 开发命令`:

```markdown
### ANP 插件开发命令

```bash
# 安装插件
pip install -e "plugins/anp-agent[dev]"

# 运行插件测试
pytest plugins/anp-agent/tests -v

# 运行单个测试
pytest plugins/anp-agent/tests/test_identity.py -v

# 启动 Hermes gateway 并启用 ANP 插件
ANP_ALLOW_ALL_USERS=1 hermes gateway run
```
```

- [ ] **Step 5: 提交**

```bash
git add plugins/anp-agent/tests/test_integration.py plugins/anp-agent/README.md CLAUDE.md
git commit -m "docs: add integration tests and plugin README"
```

---

## Task 9: 代码质量与 CI

**Files:**
- Create: `pyproject.toml`（项目根目录）
- Create: `.github/workflows/ci.yml`（可选）
- Modify: `plugins/anp-agent/pyproject.toml`（补充 lint/format 工具）

- [ ] **Step 1: 配置 ruff 和 black**

Create `/home/peter/anp-hermes/pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "N", "UP", "B", "C4", "SIM"]

[tool.black]
line-length = 100
target-version = ["py310"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["plugins/anp-agent/tests"]
```

- [ ] **Step 2: 在插件 `pyproject.toml` 中添加 dev 依赖**

Append to `plugins/anp-agent/pyproject.toml` optional-dependencies `dev`:

```toml
    "ruff>=0.6.0",
    "black>=24.0.0",
    "pytest-cov>=5.0.0",
```

- [ ] **Step 3: 运行 lint/format**

```bash
cd /home/peter/anp-hermes
ruff check plugins/anp-agent
black --check plugins/anp-agent
```

- [ ] **Step 4: 运行带覆盖率的测试**

```bash
pytest plugins/anp-agent/tests --cov=anp_agent --cov-report=term-missing
```

Expected: 覆盖率 ≥ 85%。

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml plugins/anp-agent/pyproject.toml
git commit -m "chore: add lint, format, and coverage configuration"
```

---

## Spec Coverage Check

对照完整设计文档 `/home/peter/anp-hermes/docs/superpowers/specs/2026-07-03-anp-hermes-plugin-design.md`：

| 设计章节 | 覆盖任务 |
|---|---|
| §1 背景与目标 | Task 1 骨架、Task 8 README |
| §2 系统边界 | Task 4-7 adapter/bridge/server |
| §3 目录结构 | Task 1、各任务文件创建 |
| §4 数据流 | Task 4 bridge、Task 6 server、Task 7 adapter |
| §5 关键决策 | 各任务实现 |
| §6 配置项 | Task 2 config.py |
| §7 错误处理 | Task 5 server、Task 6 签名验证 |
| §8 测试策略 | Task 3/4/5/6/8 测试 |
| §9 风险 | Task 4 TTL、Task 6 验证、Task 9 覆盖率 |
| §10 部署 | Task 8 README |
| §11 后续待办 | 不实现 |

无遗漏。

---

## Placeholder Scan

- 无 TBD/TODO/"implement later"。
- 每个测试步骤包含实际测试代码。
- 每个实现步骤包含实际代码。
- 类型和函数名在任务间一致：`ANPConfig`, `IdentityManager`, `ANPBridge`, `ANPAdapter`, `create_app`。

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-07-03-anp-hermes-plugin.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | issues_open | 7 architecture + 7 code-quality + 1 test-gap + 4 performance + 5 outside-voice issues |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **CODEX:** Not available; outside voice via Claude subagent.
- **CROSS-MODEL:** Outside voice independently flagged: unvalidated Hermes `handle_message`/`send` contract, fabricated `DidWbaVerifier` API, integration test cannot resolve caller DID, default data dir collides with plugin install dir, missing `pytest-aiohttp` dependency. These were partially missed by the main review and have been added as tasks.
- **UNRESOLVED:** 0 user-decided items remaining.
- **VERDICT:** Eng Review required — plan has open issues that must be addressed during implementation.

### Key decisions from this review

1. **Scope:** Proceed with the full plan (core plugin + lint/CI/integration tests + resilience improvements).
2. **Prerequisites:** Verify ANP SDK API signatures and Hermes `handle_message`/`send` contract before implementing bridge/auth.
3. **DID resolution:** Use real ANP SDK verifier, add in-memory DID cache with TTL, reuse `ClientSession`, add explicit resolver timeout.
4. **Data directory:** Separate default data dir from plugin install dir (e.g. `~/.hermes/data/anp-agent/`).
5. **Future cleanup:** Background asyncio TTL cleanup + max pending futures limit + explicit task cancellation in `disconnect()`.
6. **Hermes mocks:** Remove inline mock fallbacks from production code; centralize test mocks in `tests/conftest.py`.
7. **Auth errors:** Return generic JSON-RPC errors to callers; log detailed exceptions server-side.
8. **DID load resilience:** Validate loaded DID documents and regenerate + backup on corruption.
9. **Configuration:** Declarative config table, env > yaml > default, expanded validation, default timeouts lowered (request_timeout 60s, future_ttl 120s).
10. **TLS:** Optional TLS cert/key config + production reverse proxy documentation.
11. **Send semantics:** Return `success=False` for unknown `chat_id` instead of dummy success.
12. **is_connected:** Remove or implement real connected-state callback; do not return always-True.
13. **_set_fatal_error:** Remove undocumented call; return `False` from `connect()` and log exception.
14. **Body size limit:** Set `client_max_size` on aiohttp app.
15. **OpenRPC schema:** Declare `chat` result as object with `response: string`.
16. **Integration test:** Host caller DID document on a local test server so resolution succeeds.
17. **Adapter approach:** Keep `BasePlatformAdapter` platform-plugin approach per project constraints.
18. **Distribution:** Add GitHub Actions CI and document install/publish steps.

### Implementation tasks

Synthesized from this review. Run with Claude Code or Codex; checkbox as you ship.

- [ ] **T1 (P1, human: ~1h / CC: ~15min)** — research — Verify ANP SDK API and Hermes handle_message/send contract
  - Surfaced by: Outside voice OV3/OV4
  - Files: `plugins/anp-agent/adapter.py`, `plugins/anp-agent/bridge.py`
  - Verify: short spike script + notes

- [ ] **T2 (P1, human: ~1h / CC: ~15min)** — config — Declarative config table, validation, and lower default timeouts
  - Surfaced by: Code quality Q1/Q5 + performance P3
  - Files: `plugins/anp-agent/constants.py`, `plugins/anp-agent/config.py`
  - Verify: `pytest plugins/anp-agent/tests/test_config.py -v`

- [ ] **T3 (P1, human: ~1.5h / CC: ~20min)** — identity — Separate data dir, validate DID, auto-recover corruption, extract key helper
  - Surfaced by: Architecture A7 + outside voice OV1 + code quality Q4
  - Files: `plugins/anp-agent/identity.py`
  - Verify: `pytest plugins/anp-agent/tests/test_identity.py -v`

- [ ] **T4 (P1, human: ~3h / CC: ~45min)** — auth — Real ANP SDK verifier, DID cache, ClientSession reuse, generic auth errors
  - Surfaced by: Architecture A1 + performance P4 + code quality Q2
  - Files: `plugins/anp-agent/auth.py`, `plugins/anp-agent/server.py`
  - Verify: `pytest plugins/anp-agent/tests/test_server.py -v`

- [ ] **T5 (P1, human: ~2h / CC: ~30min)** — bridge-server — Remove production mocks, add body size limit, max pending futures, background TTL cleanup
  - Surfaced by: Architecture A4 + performance P1/P2
  - Files: `plugins/anp-agent/bridge.py`, `plugins/anp-agent/server.py`
  - Verify: `pytest plugins/anp-agent/tests/test_bridge.py plugins/anp-agent/tests/test_server.py -v`

- [ ] **T6 (P1, human: ~1.5h / CC: ~20min)** — adapter — Track background tasks, fix send semantics, remove _set_fatal_error, fix is_connected
  - Surfaced by: Architecture A3/A5 + code quality Q3/Q6
  - Files: `plugins/anp-agent/adapter.py`
  - Verify: `pytest plugins/anp-agent/tests/test_adapter.py -v`

- [ ] **T7 (P2, human: ~1h / CC: ~15min)** — docs-config — Optional TLS config and production reverse proxy documentation
  - Surfaced by: Architecture A2
  - Files: `plugins/anp-agent/server.py`, `plugins/anp-agent/README.md`
  - Verify: manual README review

- [ ] **T8 (P2, human: ~1.5h / CC: ~20min)** — infra — GitHub Actions CI, publish docs, and add pytest-aiohttp dev dependency
  - Surfaced by: Architecture A6 + outside voice missing pytest-aiohttp
  - Files: `.github/workflows/ci.yml`, `plugins/anp-agent/pyproject.toml`
  - Verify: CI run passes

- [ ] **T9 (P1, human: ~4h / CC: ~1h)** — tests — Add 27 missing test paths and local DID server for integration test
  - Surfaced by: Test review D3 + outside voice OV2
  - Files: `plugins/anp-agent/tests/*.py`, `plugins/anp-agent/tests/conftest.py`
  - Verify: `pytest plugins/anp-agent/tests --cov=anp_agent --cov-report=term-missing`

- [ ] **T10 (P3, human: ~30min / CC: ~5min)** — server — Change chat result schema from scalar string to structured object
  - Surfaced by: Code quality Q7
  - Files: `plugins/anp-agent/server.py`
  - Verify: `pytest plugins/anp-agent/tests/test_server.py::test_interface_json -v`

- [ ] **T11 (P1, human: ~30min / CC: ~5min)** — auth — Add explicit timeout to DID document HTTP resolution
  - Surfaced by: Failure modes analysis — unresolved caller DID host causes RPC hang
  - Files: `plugins/anp-agent/auth.py`
  - Verify: `pytest plugins/anp-agent/tests/test_server.py -v`


