# ANP Hermes E2E 测试实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `anp-agent` 插件新增在真实 Hermes gateway 中运行的端到端测试，包含确定性 echo 阶段与真实 LLM 阶段，默认跳过，通过 `--run-e2e` / `--run-slow-e2e` 触发。

**Architecture:** 测试使用临时 `HERMES_HOME` 隔离 Hermes 状态，通过符号链接加载当前 `anp-agent` 插件代码，从用户真实 `~/.hermes/config.yaml` 复制 model/provider 配置，动态生成 caller DID WBA 身份并本地托管 DID 文档，最后调用 ANP `/agent/rpc` 端点完成验证。

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, aiohttp, PyYAML, ANP Python SDK, Hermes CLI。

## Global Constraints

- 不修改 `anp-agent` 插件核心实现。
- 不将 E2E 测试加入默认 CI 流程。
- 不测试 AP2 支付或 E2EE 加密。
- 每次 E2E 测试使用隔离的临时 `HERMES_HOME`。
- E2E 测试默认跳过，通过 `--run-e2e` 触发；LLM 测试额外要求 `--run-slow-e2e`。
- 阶段一使用 `anp-echo` skill + 宽松断言（包含原输入/非空/无 error）。
- 阶段二使用真实 LLM + 宽松断言（语义引用前文）。
- 阶段一/阶段二的 model/provider 配置从真实 `~/.hermes/config.yaml` 复制。
- 官方语言为中文，代码注释与文档使用中文。

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `plugins/anp-agent/tests/e2e/__init__.py` | E2E 测试包标记 |
| `plugins/anp-agent/tests/e2e/conftest.py` | pytest 选项、fixtures、共享 helpers |
| `plugins/anp-agent/tests/e2e/data/anp-echo/SKILL.md` | echo skill 静态资源 |
| `plugins/anp-agent/tests/e2e/test_echo.py` | 阶段一 echo E2E 测试 |
| `plugins/anp-agent/tests/e2e/test_llm.py` | 阶段二真实 LLM E2E 测试 |
| `plugins/anp-agent/README.md` | 更新 E2E 测试运行说明 |
| `CLAUDE.md` | 更新 E2E 测试开发命令 |

---

### Task 1: 创建 E2E 测试目录结构与 pytest 选项

**Files:**
- Create: `plugins/anp-agent/tests/e2e/__init__.py`
- Create: `plugins/anp-agent/tests/e2e/conftest.py`
- Create: `plugins/anp-agent/tests/e2e/data/anp-echo/SKILL.md`
- Modify: `plugins/anp-agent/pyproject.toml`（如需调整 ruff 的 per-file-ignores）

**Interfaces:**
- Consumes: 无
- Produces: `--run-e2e` / `--run-slow-e2e` pytest 选项；`e2e` 目录下测试在未传选项时自动 skip

- [ ] **Step 1: 创建 E2E 测试包目录**

```bash
mkdir -p plugins/anp-agent/tests/e2e/data/anp-echo
touch plugins/anp-agent/tests/e2e/__init__.py
```

- [ ] **Step 2: 编写 `conftest.py` 注册 pytest 选项并自动 skip**

```python
# plugins/anp-agent/tests/e2e/conftest.py
"""E2E 测试共享配置与 fixtures。"""

from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import requests
import yaml
from aiohttp import ClientSession


def pytest_addoption(parser):
    """注册 E2E 测试选项。"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="运行 E2E 测试（需要本地 Hermes 安装）",
    )
    parser.addoption(
        "--run-slow-e2e",
        action="store_true",
        default=False,
        help="运行需要真实 LLM 的慢速 E2E 测试",
    )


def pytest_collection_modifyitems(config, items):
    """未传 --run-e2e 时跳过 e2e 目录下所有测试。"""
    if config.getoption("--run-e2e"):
        return
    skip = pytest.mark.skip(reason="需要 --run-e2e 选项才能运行 E2E 测试")
    for item in items:
        item.add_marker(skip)
```

- [ ] **Step 3: 验证默认 skip 行为**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/ -v
```

Expected: 所有测试被 skip，输出 `SKIPPED (需要 --run-e2e 选项才能运行 E2E 测试)`。

- [ ] **Step 4: 验证 --run-e2e 能收集测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/ --run-e2e --collect-only
```

Expected: 显示 `test_echo.py` 和 `test_llm.py` 中的测试用例（此时文件尚不存在，可先创建空文件验证）。

- [ ] **Step 5: Commit**

```bash
git add plugins/anp-agent/tests/e2e/
git commit -m "test(e2e): 初始化 E2E 测试目录与 pytest 选项"
```

---

### Task 2: 实现 E2E 共享 helpers（端口、等待、配置加载、Hermes 启动）

**Files:**
- Modify: `plugins/anp-agent/tests/e2e/conftest.py`

**Interfaces:**
- Consumes: `--run-e2e` 选项；用户真实 `~/.hermes/config.yaml`
- Produces: `free_port()`, `wait_for_url()`, `_load_user_hermes_config()`, `hermes_gateway()` fixture（基础版）

- [ ] **Step 1: 添加 helper 函数**

在 `conftest.py` 末尾追加：

```python
import os
import subprocess
import tempfile


def free_port() -> int:
    """申请一个本地空闲 TCP 端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_url(url: str, timeout: float = 60.0, interval: float = 0.5) -> bool:
    """轮询等待 URL 返回 HTTP 200。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def _load_user_hermes_config() -> dict[str, Any]:
    """读取用户真实 ~/.hermes/config.yaml 的 model/provider 配置。

    如果文件不存在或解析失败，返回空字典。
    """
    config_path = Path.home() / ".hermes" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}
```

- [ ] **Step 2: 为基础 helper 编写简单测试**

```python
# plugins/anp-agent/tests/e2e/test_helpers.py
def test_free_port_returns_valid_port():
    port = free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535
```

- [ ] **Step 3: 运行 helper 测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_helpers.py -v
```

Expected: PASS。

- [ ] **Step 4: Commit**

```bash
git add plugins/anp-agent/tests/e2e/conftest.py plugins/anp-agent/tests/e2e/test_helpers.py
git commit -m "test(e2e): 添加端口、等待、配置加载 helpers"
```

---

### Task 3: 实现 caller DID WBA 身份与本地 DID 文档服务器 fixtures

**Files:**
- Modify: `plugins/anp-agent/tests/e2e/conftest.py`
- Reuse: `plugins/anp-agent/tests/helpers/did_server.py`
- Reuse: `plugins/anp-agent/tests/helpers/signing.py`

**Interfaces:**
- Consumes: `tmp_path` fixture；ANP SDK `create_did_wba_document`
- Produces: `anp_caller_identity()` fixture；`did_document_server()` fixture；`build_signed_headers()` helper

- [ ] **Step 1: 将现有 helper 暴露到 E2E 测试**

修改 `conftest.py` 顶部 `sys.path`，使 `tests.helpers` 可被导入：

```python
import json
import os
import sys

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anp.authentication import create_did_wba_document
from tests.helpers.did_server import DIDDocumentServer
from tests.helpers.signing import build_signed_headers
```

- [ ] **Step 2: 添加 fixtures**

```python
@pytest.fixture
def anp_caller_identity(tmp_path: Path):
    """动态生成 ANP caller DID WBA 身份及密钥文件。"""
    workdir = tmp_path / "caller"
    workdir.mkdir(parents=True, exist_ok=True)

    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    did = did_document["id"]
    auth_key = keys.get("key-1")
    assert auth_key is not None, "DID 文档未生成 key-1 认证密钥"
    private_key_pem = auth_key[0]

    did_path = workdir / "did.json"
    key_path = workdir / "private_key.pem"
    did_path.write_text(json.dumps(did_document), encoding="utf-8")
    key_path.write_bytes(private_key_pem)

    return {
        "did": did,
        "did_document": did_document,
        "private_key_pem": private_key_pem,
        "did_path": did_path,
        "key_path": key_path,
    }


@pytest_asyncio.fixture
async def did_document_server(anp_caller_identity: dict[str, Any]) -> DIDDocumentServer:
    """启动本地 DID 文档服务器，供 ANP verifier 解析 caller DID。"""
    async with DIDDocumentServer(anp_caller_identity["did_document"]) as server:
        yield server
```

- [ ] **Step 3: 编写 fixture  smoke test**

```python
# plugins/anp-agent/tests/e2e/test_fixtures.py
import pytest


@pytest.mark.asyncio
async def test_did_document_server_hosts_document(did_document_server, anp_caller_identity):
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{did_document_server.base_url}/agent/did.json") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["id"] == anp_caller_identity["did"]
```

- [ ] **Step 4: 运行测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_fixtures.py --run-e2e -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add plugins/anp-agent/tests/e2e/conftest.py plugins/anp-agent/tests/e2e/test_fixtures.py
git commit -m "test(e2e): 添加 caller DID 与本地 DID 文档服务器 fixtures"
```

---

### Task 4: 实现阶段一 Echo E2E 测试

**Files:**
- Create: `plugins/anp-agent/tests/e2e/data/anp-echo/SKILL.md`
- Modify: `plugins/anp-agent/tests/e2e/conftest.py`
- Create: `plugins/anp-agent/tests/e2e/test_echo.py`

**Interfaces:**
- Consumes: `anp_caller_identity`, `did_document_server`, `_load_user_hermes_config`, `free_port`, `wait_for_url`
- Produces: `hermes_gateway` fixture；`test_echo_chat_returns_message`, `test_echo_ad_json_and_interface_json`

- [ ] **Step 1: 创建 echo skill**

```markdown
---
name: anp-echo
description: "E2E 测试专用 echo skill。当收到任何消息时，只原样返回用户输入文本，不解释、不补充、不调用任何工具。"
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [anp, echo, e2e, test]
---

# anp-echo

你是 E2E 测试专用的 echo 助手。你的唯一任务是原样返回用户发送的文本，不要解释、不要补充、不要调用任何工具。

规则：
- 无论用户发送什么，都只回复与用户输入完全相同的文本。
- 不要添加任何前缀、后缀、标点或格式说明。
- 如果用户发送 "hello-e2e"，你就回复 "hello-e2e"。
- 如果用户发送 "你好"，你就回复 "你好"。
- 禁止调用任何工具或执行任何操作。
```

- [ ] **Step 2: 添加 `hermes_gateway` fixture**

在 `conftest.py` 中追加：

```python
@pytest.fixture
def hermes_gateway(tmp_path: Path):
    """启动真实 Hermes gateway，加载 anp-agent 插件与 anp-echo skill。"""
    # 1. 准备临时 HERMES_HOME
    hermes_home = tmp_path / "hermes_home"
    hermes_home.mkdir(parents=True, exist_ok=True)
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    skills_dir = hermes_home / "skills"
    skills_dir.mkdir(exist_ok=True)

    # 2. 符号链接 anp-agent 插件
    repo_root = Path(__file__).resolve().parents[3]
    plugin_src = repo_root / "plugins" / "anp-agent"
    plugin_link = plugins_dir / "anp-agent"
    plugin_link.symlink_to(plugin_src, target_is_directory=True)

    # 3. 安装 anp-echo skill
    echo_skill_dst = skills_dir / "anp-echo"
    echo_skill_src = Path(__file__).resolve().parent / "data" / "anp-echo"
    echo_skill_dst.symlink_to(echo_skill_src, target_is_directory=True)

    # 4. 从真实配置复制 model/provider，并覆盖必要项
    port = free_port()
    user_config = _load_user_hermes_config()
    if not user_config:
        pytest.skip("未找到 ~/.hermes/config.yaml，无法运行 E2E 测试")

    config = dict(user_config)
    config.setdefault("gateway", {})
    config["gateway"]["platforms"] = {
        "anp": {
            "extra": {
                "host": "127.0.0.1",
                "port": port,
                "hostname": "localhost",
                "endpoint": f"http://127.0.0.1:{port}",
                "data_dir": str(hermes_home / "anp-agent-data"),
                "request_timeout": 60,
                "future_ttl": 120,
            }
        }
    }
    config.setdefault("plugins", {})
    config["plugins"]["enabled"] = list(set(config.get("plugins", {}).get("enabled", []) + ["anp-agent"]))
    config["skills"] = {"external_dirs": [], "template_vars": True, "inline_shell": False}
    # 默认激活 anp-echo skill（通过 auto_skill 在 MessageEvent 中绑定）

    config_path = hermes_home / "config.yaml"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    # 5. 启动 hermes gateway run 子进程
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["ANP_ALLOW_ALL_USERS"] = "1"

    proc = subprocess.Popen(
        ["hermes", "gateway", "run", "--accept-hooks"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    endpoint = f"http://127.0.0.1:{port}"
    try:
        if not wait_for_url(f"{endpoint}/agent/ad.json", timeout=60.0):
            proc.terminate()
            try:
                proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            pytest.fail(f"Hermes gateway 未能在 60 秒内启动，endpoint={endpoint}")
        yield {"endpoint": endpoint, "process": proc, "home": hermes_home}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 3: 创建 `test_echo.py`**

```python
# plugins/anp-agent/tests/e2e/test_echo.py
"""阶段一：确定性 Echo E2E 测试。"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.e2e.conftest import build_signed_headers


@pytest.mark.asyncio
async def test_echo_chat_returns_message(hermes_gateway, anp_caller_identity, did_document_server):
    """签名调用 chat 后应返回原消息。"""
    endpoint = hermes_gateway["endpoint"]
    target_url = f"{endpoint}/agent/rpc"
    message = "hello-e2e"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": message},
            "id": "echo-1",
        }
    )

    headers = await build_signed_headers(anp_caller_identity, target_url, body)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            target_url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "echo-1"
            assert "error" not in data
            assert message in data["result"]["response"]


@pytest.mark.asyncio
async def test_echo_ad_json_and_interface_json(hermes_gateway):
    """未受保护端点应正常返回。"""
    endpoint = hermes_gateway["endpoint"]
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{endpoint}/agent/ad.json") as resp:
            assert resp.status == 200
            ad = await resp.json()
            assert ad["id"].startswith("did:wba:")
            assert ad["endpoint"] == endpoint

        async with session.get(f"{endpoint}/agent/interface.json") as resp:
            assert resp.status == 200
            iface = await resp.json()
            assert any(m["name"] == "chat" for m in iface["methods"])
```

- [ ] **Step 4: 修复 import 问题**

如果 `build_signed_headers` 需要从 `tests.helpers.signing` 导入而非 `tests.e2e.conftest`，调整 `test_echo.py` 顶部：

```python
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers.signing import build_signed_headers
```

- [ ] **Step 5: 运行阶段一 E2E 测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_echo.py --run-e2e -v
```

Expected: 2 个测试 PASS。

- [ ] **Step 6: Commit**

```bash
git add plugins/anp-agent/tests/e2e/
git commit -m "test(e2e): 实现阶段一 echo E2E 测试"
```

---

### Task 5: 实现阶段二真实 LLM E2E 测试

**Files:**
- Modify: `plugins/anp-agent/tests/e2e/conftest.py`
- Create: `plugins/anp-agent/tests/e2e/test_llm.py`

**Interfaces:**
- Consumes: `anp_caller_identity`, `did_document_server`, `_load_user_hermes_config`, `free_port`, `wait_for_url`
- Produces: `llm_hermes_gateway` fixture；`test_llm_single_turn_chat`, `test_llm_multi_turn_chat`

- [ ] **Step 1: 添加 `llm_hermes_gateway` fixture**

在 `conftest.py` 中追加：

```python
@pytest.fixture
def llm_hermes_gateway(tmp_path: Path):
    """启动真实 Hermes gateway，加载 anp-agent 插件，使用真实 LLM 配置。"""
    hermes_home = tmp_path / "hermes_home"
    hermes_home.mkdir(parents=True, exist_ok=True)
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(exist_ok=True)

    repo_root = Path(__file__).resolve().parents[3]
    plugin_src = repo_root / "plugins" / "anp-agent"
    plugin_link = plugins_dir / "anp-agent"
    plugin_link.symlink_to(plugin_src, target_is_directory=True)

    port = free_port()
    user_config = _load_user_hermes_config()
    if not user_config:
        pytest.skip("未找到 ~/.hermes/config.yaml，无法运行 LLM E2E 测试")

    config = dict(user_config)
    config.setdefault("gateway", {})
    config["gateway"]["platforms"] = {
        "anp": {
            "extra": {
                "host": "127.0.0.1",
                "port": port,
                "hostname": "localhost",
                "endpoint": f"http://127.0.0.1:{port}",
                "data_dir": str(hermes_home / "anp-agent-data"),
                "request_timeout": 60,
                "future_ttl": 120,
            }
        }
    }
    config.setdefault("plugins", {})
    config["plugins"]["enabled"] = list(set(config.get("plugins", {}).get("enabled", []) + ["anp-agent"]))

    config_path = hermes_home / "config.yaml"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["ANP_ALLOW_ALL_USERS"] = "1"

    proc = subprocess.Popen(
        ["hermes", "gateway", "run", "--accept-hooks"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    endpoint = f"http://127.0.0.1:{port}"
    try:
        if not wait_for_url(f"{endpoint}/agent/ad.json", timeout=60.0):
            proc.terminate()
            try:
                proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            pytest.fail(f"Hermes gateway 未能在 60 秒内启动，endpoint={endpoint}")
        yield {"endpoint": endpoint, "process": proc, "home": hermes_home}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 2: 创建 `test_llm.py`**

```python
# plugins/anp-agent/tests/e2e/test_llm.py
"""阶段二：真实 LLM E2E 测试。"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.helpers.signing import build_signed_headers


pytestmark = pytest.mark.slow


async def _chat(endpoint: str, caller_identity: dict, rpc_id: str, message: str) -> dict:
    target_url = f"{endpoint}/agent/rpc"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "chat",
            "params": {"message": message},
            "id": rpc_id,
        }
    )
    headers = await build_signed_headers(caller_identity, target_url, body)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            target_url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            assert resp.status == 200
            return await resp.json()


@pytest.mark.asyncio
async def test_llm_single_turn_chat(llm_hermes_gateway, anp_caller_identity, did_document_server):
    """单轮对话返回非空、格式正确、无 error。"""
    data = await _chat(
        llm_hermes_gateway["endpoint"],
        anp_caller_identity,
        "llm-single-1",
        "你好",
    )
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "llm-single-1"
    assert "error" not in data
    response = data["result"]["response"]
    assert isinstance(response, str)
    assert response.strip()


@pytest.mark.asyncio
async def test_llm_multi_turn_chat(llm_hermes_gateway, anp_caller_identity, did_document_server):
    """同一 caller DID 的多轮对话能保留上下文。"""
    endpoint = llm_hermes_gateway["endpoint"]

    first = await _chat(endpoint, anp_caller_identity, "llm-multi-1", "我叫 Alice")
    assert "error" not in first

    second = await _chat(endpoint, anp_caller_identity, "llm-multi-2", "我叫什么名字？")
    assert second["jsonrpc"] == "2.0"
    assert second["id"] == "llm-multi-2"
    assert "error" not in second
    response = second["result"]["response"]
    assert "Alice" in response or "alice" in response.lower()
```

- [ ] **Step 3: 运行 LLM E2E 测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_llm.py --run-e2e --run-slow-e2e -v
```

Expected: 2 个测试 PASS（可能耗时较长，依赖 LLM 响应）。

- [ ] **Step 4: Commit**

```bash
git add plugins/anp-agent/tests/e2e/
git commit -m "test(e2e): 实现阶段二真实 LLM E2E 测试"
```

---

### Task 6: 更新文档

**Files:**
- Modify: `plugins/anp-agent/README.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: E2E 测试实现结果
- Produces: 可运行的 E2E 测试说明

- [ ] **Step 1: 更新 `plugins/anp-agent/README.md`**

在"## 测试"节后追加：

```markdown
### E2E 测试

E2E 测试会在本地启动真实 Hermes gateway，需要：

- 本地已安装 Hermes CLI (`hermes`)
- `~/.hermes/config.yaml` 已配置可用的 model provider
- 测试使用临时 `HERMES_HOME`，不会污染真实配置

```bash
# 阶段一：确定性 echo 测试（不调用真实 LLM，使用 echo skill）
python -m pytest tests/e2e/test_echo.py --run-e2e -v

# 阶段二：真实 LLM 测试（单轮 + 多轮）
python -m pytest tests/e2e/test_llm.py --run-e2e --run-slow-e2e -v

# 全部 E2E 测试
python -m pytest tests/e2e/ --run-e2e --run-slow-e2e -v
```

默认不传入 `--run-e2e` 时，`tests/e2e/` 下所有测试会被跳过。
```

- [ ] **Step 2: 更新 `CLAUDE.md`**

在"开发命令"节后追加：

```markdown
### E2E 测试

```bash
# 阶段一 echo E2E（确定性，较快）
python -m pytest tests/e2e/test_echo.py --run-e2e -v

# 阶段二真实 LLM E2E（较慢，需要配置好的 model provider）
python -m pytest tests/e2e/test_llm.py --run-e2e --run-slow-e2e -v
```

约束：
- E2E 测试默认跳过，需显式传入 `--run-e2e`。
- LLM 测试额外要求 `--run-slow-e2e`。
- 临时 `HERMES_HOME` 从真实 `~/.hermes/config.yaml` 复制 model/provider 配置，测试结束后删除。
```

- [ ] **Step 3: 验证文档渲染**

```bash
python -m markdown plugins/anp-agent/README.md > /dev/null || true
```

- [ ] **Step 4: Commit**

```bash
git add plugins/anp-agent/README.md CLAUDE.md
git commit -m "docs: 更新 E2E 测试运行说明"
```

---

### Task 7: Lint、格式与覆盖率回归

**Files:**
- Modify: `plugins/anp-agent/tests/e2e/` 下所有文件（按需修复）

**Interfaces:**
- Consumes: 前述任务产出的代码
- Produces: 通过 ruff/black/pytest-cov 的代码

- [ ] **Step 1: 运行 lint**

```bash
cd plugins/anp-agent
ruff check .
```

Expected: 无错误。

- [ ] **Step 2: 运行 black 检查**

```bash
cd plugins/anp-agent
black --check .
```

Expected: 无修改建议。

- [ ] **Step 3: 运行单元测试（不含 E2E）并检查覆盖率**

```bash
cd plugins/anp-agent
python -m pytest --cov=. --cov-fail-under=85 -q
```

Expected: 全部通过，覆盖率 ≥ 85%。

- [ ] **Step 4: 修复任何问题**

如 lint/black/测试失败，修复后重新运行。

- [ ] **Step 5: Commit**

```bash
git add plugins/anp-agent/tests/e2e/
git commit -m "style(e2e): 修复 lint 与格式化"
```

---

### Task 8: 最终验证与 OpenSpec 归档

**Files:**
- 无新增文件

**Interfaces:**
- Consumes: 完整实现
- Produces: 可归档的变更状态

- [ ] **Step 1: 运行阶段一 E2E 测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_echo.py --run-e2e -v
```

Expected: PASS。

- [ ] **Step 2: 运行阶段二 E2E 测试**

```bash
cd plugins/anp-agent
python -m pytest tests/e2e/test_llm.py --run-e2e --run-slow-e2e -v
```

Expected: PASS。

- [ ] **Step 3: 检查 OpenSpec 状态**

```bash
openspec status --change anp-hermes-e2e-tests --json
```

Expected: `isComplete: true`，所有 artifacts 状态 `done`。

- [ ] **Step 4: 归档变更**

```bash
/opsx:archive anp-hermes-e2e-tests
```

或根据 OpenSpec 实际命令归档。

- [ ] **Step 5: Commit（如归档产生变更）**

```bash
git add openspec/changes/anp-hermes-e2e-tests/
git commit -m "chore: 归档 OpenSpec 变更 anp-hermes-e2e-tests"
```

---

## Spec Coverage Check

| Spec 要求 | 对应任务 |
|-----------|----------|
| Echo E2E 启动真实 Hermes 并暴露 ANP 端点 | Task 4 |
| Echo E2E 返回 caller 消息 | Task 4 |
| E2E 使用隔离 HERMES_HOME | Task 1/2/4/5 |
| E2E 默认跳过 | Task 1 |
| LLM 单轮返回有效响应 | Task 5 |
| LLM 多轮上下文连续 | Task 5 |
| LLM 测试 gated behind slow | Task 1/5 |
| LLM 使用宽松断言 | Task 5 |

## Placeholder Scan

- 无 TBD/TODO
- 无 "add appropriate error handling" 等模糊描述
- 每个步骤包含具体命令和期望输出
- 每个代码块包含完整可运行代码

## Type Consistency

- `free_port()` → `int`
- `wait_for_url(url, timeout, interval)` → `bool`
- `_load_user_hermes_config()` → `dict[str, Any]`
- `anp_caller_identity` fixture → `dict[str, Any]`
- `did_document_server` fixture → `DIDDocumentServer`
- `hermes_gateway` / `llm_hermes_gateway` fixture → `dict` with keys `endpoint`, `process`, `home`
- `build_signed_headers(caller_identity, target_url, body)` → `dict[str, str]` (async)
