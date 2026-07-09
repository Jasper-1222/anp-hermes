# Add ANP Client Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个自包含 `anp-client` skill 安装包，让个人智能体通过 ANP DID WBA 签名发现并调用安装 Hermes `anp-agent` plugin 的服务智能体。

**Architecture:** 在 `clients/anp-client/` 下新增可独立安装的 skill 目录；运行时代码拆成 DID 身份、DID 文档服务、签名、CLI/discovery/chat 四个小模块。CLI 使用直接 URL 发现服务智能体，使用 legacy JSON-RPC `params.message` 调用 `chat`，并通过固定自然语言样例夹具验证 `SKILL.md` 承诺的自然语言入口。

**Tech Stack:** Python 3.10+、`aiohttp>=3.9.0`、`anp>=0.8.8,<0.9.0`、`cryptography>=42.0.0`、`base58>=2.1.1`、pytest、pytest-asyncio、Hermes gateway E2E harness。

## Global Constraints

- 官方语言为中文：文档、注释、业务语义命名、提交信息、Issue/PR 描述均使用中文。
- 所有操作必须在 WSL2 中执行，禁止调用 Windows 路径。
- 新增 skill 根目录为 `clients/anp-client/`，通用安装包根目录至少包含 `SKILL.md`、`README.md`、`requirements.txt` 和 `scripts/`，发布包不得依赖仓库外相对软链接或本机绝对路径。
- 安装 `anp-client` skill 的调用方称为“个人智能体”；安装 Hermes `anp-agent` plugin 的被调用方称为“服务智能体”。
- 默认身份目录为 `~/.anp-client/`，可通过 `ANP_CLIENT_HOME` 覆盖。
- 私钥文件 `private_key.pem` 权限必须为 `0o600`。
- 身份文件缺失一部分、损坏或无法解析时必须返回明确错误，不得静默生成新 DID 覆盖现有身份。
- `serve-did` 默认只能监听 loopback 地址；本地 DID 文档服务仅用于本地开发、测试和 E2E。
- endpoint 安全策略：只允许 loopback HTTP (`localhost`、`127.0.0.1`、`::1`) 与 HTTPS；必须拒绝非 loopback 明文 HTTP。
- Phase 1 signed `chat` 验收只承诺同机 loopback 服务智能体；HTTPS URL 仅表示传输安全策略允许，远程 HTTPS 服务若无法解析 `did:wba:localhost...` caller DID 会认证失败。生产/跨机器调用需要后续 change 增加公开 DID 托管或初始化能力。
- 第一期 chat 使用 legacy JSON-RPC `params.message`，不默认使用 Core Binding envelope。
- 第一期不得调用 `hermes.tool.*`，不得执行远端工具，不得保存服务通讯录，不实现 AP2、E2EE、群聊或多轮 session 同步。
- 命令式 CLI 是稳定验收标准；自然语言入口通过 deterministic normalizer 和固定样例夹具验证。
- Commit steps in this plan are for execution sessions that have explicit commit authorization. If the current user instruction does not authorize commits, skip the commit command and report the exact files ready to commit.

---

## File Structure

### Create

- `clients/anp-client/SKILL.md`  
  Skill 入口说明。定义个人智能体/服务智能体术语、自然语言触发规则、命令式调用、能力边界和安全限制。

- `clients/anp-client/README.md`  
  面向用户的安装、依赖、最小本地 E2E、故障排查和生产 DID 托管说明。

- `clients/anp-client/requirements.txt`  
  自包含 skill 运行时依赖：`anp>=0.8.8,<0.9.0`、`aiohttp>=3.9.0`、`cryptography>=42.0.0`、`base58>=2.1.1`。

- `clients/anp-client/requirements-dev.txt`  
  源码仓库验证依赖：pytest、pytest-asyncio、black、ruff；不要求进入最终用户安装包。

- `clients/anp-client/scripts/did_identity.py`  
  管理个人智能体 DID WBA 身份：默认目录、环境变量覆盖、生成、加载、校验、私钥权限。

- `clients/anp-client/scripts/did_server.py`  
  本地 loopback DID 文档服务：根据 DID path segments 暴露 `/agent/e1_<fingerprint>/did.json`。

- `clients/anp-client/scripts/signing.py`  
  用 `DIDWbaAuthHeader` 对实际发送的 JSON-RPC body 生成 DID WBA HTTP Signature 请求头。

- `clients/anp-client/scripts/anp_client.py`  
  CLI 入口和业务编排：`whoami`、`serve-did`、`discover`、`chat`、URL 安全校验、AD/OpenRPC 解析、JSON 输出、错误提示、自然语言样例 normalizer。

- `clients/anp-client/tests/conftest.py`  
  将 `clients/anp-client/scripts/` 加入测试 import path，提供临时 `ANP_CLIENT_HOME` 和本地 `aiohttp_unused_port` fixture。

- `clients/anp-client/tests/test_identity.py`  
  测试 DID 身份生成、复用、权限、损坏错误和 `ANP_CLIENT_HOME` 覆盖。

- `clients/anp-client/tests/test_discovery.py`  
  测试 URL 安全策略、endpoint/ad-url Agent Description/OpenRPC 解析、`discover --json` 输出结构、缺少 `chat` 的 discover/chat 差异行为和 HTTP 错误。

- `clients/anp-client/tests/test_chat.py`  
  测试 JSON-RPC `chat` body、签名头、错误提示映射、HTTP/JSON-RPC 错误和 `--json` 成功输出解析。

- `clients/anp-client/tests/test_cli.py`  
  测试 CLI 子命令解析、返回码和 stdout/stderr 基本契约。

- `clients/anp-client/tests/test_natural_language_examples.py`  
  测试固定自然语言样例到命令式参数的 deterministic normalizer。

- `clients/anp-client/tests/test_package_boundary.py`  
  测试 self-contained skill 安装包边界：无运行态 DID/私钥、无软链接、无仓库绝对路径依赖。

- `plugins/anp-agent/tests/e2e/test_anp_client_skill.py`  
  基于现有 Hermes gateway fixture 的真实 E2E：用 `anp-client` CLI 发现服务智能体并发送 `chat --json`。

### Reuse / Reference

- `scripts/start_did_server.py` — caller DID 生成与 DID 文档服务原型。
- `scripts/anp_chat_client.py` — discovery + DID WBA 签名 chat 原型。
- `plugins/anp-agent/tests/helpers/signing.py` — `DIDWbaAuthHeader` 签名 helper 参考。
- `plugins/anp-agent/tests/helpers/did_server.py` — 测试用 DID 文档服务器参考。
- `plugins/anp-agent/tests/e2e/conftest.py` — 真实 Hermes gateway fixture。
- `plugins/anp-agent/tests/e2e/test_echo.py` — 当前 echo E2E 断言风格。
- `plugins/anp-agent/pyproject.toml` — 依赖版本和 pytest/ruff/black 配置参考。

---

### Task 1: Skill Skeleton, Dependencies, and Test Import Harness

**Files:**
- Create: `clients/anp-client/SKILL.md`
- Create: `clients/anp-client/README.md`
- Create: `clients/anp-client/requirements.txt`
- Create: `clients/anp-client/requirements-dev.txt`
- Create: `clients/anp-client/scripts/anp_client.py`
- Create: `clients/anp-client/scripts/did_identity.py`
- Create: `clients/anp-client/scripts/did_server.py`
- Create: `clients/anp-client/scripts/signing.py`
- Create: `clients/anp-client/tests/conftest.py`
- Create: `clients/anp-client/tests/test_package_boundary.py`
- Test: shell checks and `python3 -m pytest clients/anp-client/tests -q`

**Interfaces:**
- Consumes: none.
- Produces:
  - Importable modules from `clients/anp-client/scripts/`.
  - Placeholder-free docs with exact commands.
  - Runtime dependency list.

- [ ] **Step 1: Create the directory skeleton**

Run:

```bash
mkdir -p clients/anp-client/scripts clients/anp-client/tests
```

Expected: directories exist.

- [ ] **Step 2: Write `requirements.txt`**

Create `clients/anp-client/requirements.txt` with exactly:

```text
anp>=0.8.8,<0.9.0
aiohttp>=3.9.0
cryptography>=42.0.0
base58>=2.1.1
```

Create `clients/anp-client/requirements-dev.txt` with exactly:

```text
-r requirements.txt
pytest>=8.0.0
pytest-asyncio>=0.23.0
black>=24.0.0
ruff>=0.5.0
```

- [ ] **Step 3: Write minimal importable script modules**

Create `clients/anp-client/scripts/did_identity.py`:

```python
"""个人智能体 DID WBA 身份管理。"""

from __future__ import annotations


class IdentityError(RuntimeError):
    """个人智能体身份无法创建或加载。"""
```

Create `clients/anp-client/scripts/did_server.py`:

```python
"""个人智能体本地 DID 文档服务。"""

from __future__ import annotations
```

Create `clients/anp-client/scripts/signing.py`:

```python
"""ANP DID WBA HTTP Signature 生成。"""

from __future__ import annotations
```

Create `clients/anp-client/scripts/anp_client.py`:

```python
#!/usr/bin/env python3
"""通用 ANP client skill 命令行入口。"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="anp_client.py",
        description="个人智能体调用 ANP 服务智能体的客户端工具。",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("whoami", help="显示或创建个人智能体 DID")
    subcommands.add_parser("serve-did", help="启动本地 DID 文档服务")

    discover = subcommands.add_parser("discover", help="发现 ANP 服务智能体")
    discover.add_argument("--endpoint")
    discover.add_argument("--ad-url")
    discover.add_argument("--json", action="store_true")

    chat = subcommands.add_parser("chat", help="向 ANP 服务智能体发送 chat")
    chat.add_argument("--endpoint")
    chat.add_argument("--ad-url")
    chat.add_argument("--message", required=True)
    chat.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    """CLI 入口。"""
    parser = build_parser()
    parser.parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Write test import harness**

Create `clients/anp-client/tests/conftest.py`:

```python
"""anp-client skill 测试配置。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from aiohttp.test_utils import unused_port

CLIENT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = CLIENT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def client_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """为测试隔离 ANP_CLIENT_HOME。"""
    home = tmp_path / "anp-client-home"
    monkeypatch.setenv("ANP_CLIENT_HOME", str(home))
    return home


@pytest.fixture
def aiohttp_unused_port() -> Callable[[], int]:
    """提供空闲端口 fixture，复用 aiohttp 自带 helper，避免新增 pytest-aiohttp 依赖。"""
    return unused_port
```

- [ ] **Step 5: Write package boundary tests**

Create `clients/anp-client/tests/test_package_boundary.py`:

```python
"""anp-client skill 安装包边界测试。"""

from __future__ import annotations

from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {"did.json", "private_key.pem"}
FORBIDDEN_SUFFIXES = (".tmp", ".bak")
FORBIDDEN_ABSOLUTE_PATH = "/home/peter/anp-hermes"


def test_skill_package_contains_required_root_files() -> None:
    for relative in ["SKILL.md", "README.md", "requirements.txt", "scripts"]:
        assert (CLIENT_ROOT / relative).exists()


def test_skill_package_contains_no_runtime_identity_files() -> None:
    forbidden = [
        path
        for path in CLIENT_ROOT.rglob("*")
        if path.name in FORBIDDEN_NAMES or path.name.endswith(FORBIDDEN_SUFFIXES)
    ]
    assert forbidden == []


def test_skill_package_contains_no_symlinks() -> None:
    assert [path for path in CLIENT_ROOT.rglob("*") if path.is_symlink()] == []


def test_skill_scripts_do_not_depend_on_repo_absolute_path() -> None:
    offenders: list[Path] = []
    for path in CLIENT_ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".md", ".txt"}:
            if FORBIDDEN_ABSOLUTE_PATH in path.read_text(encoding="utf-8"):
                offenders.append(path)
    assert offenders == []
```

- [ ] **Step 6: Write initial `SKILL.md`**

Create `clients/anp-client/SKILL.md`:

```markdown
---
name: anp-client
description: 让个人智能体通过 ANP DID WBA 签名发现并调用服务智能体的通用客户端 skill。
version: 0.1.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [anp, did-wba, json-rpc, client]
---

# ANP Client Skill

你是安装在个人智能体中的 ANP 客户端 skill。个人智能体是调用方，类似互联网用户；服务智能体是安装 Hermes `anp-agent` plugin 的被调用方，类似 App 或互联网平台服务。

## 能力边界

- 你可以帮助用户发现 ANP 服务智能体。
- 你可以通过 DID WBA 签名 JSON-RPC `chat` 与服务智能体对话。
- 第一期不得调用 `hermes.tool.*`。
- 第一期不得执行远端工具。
- 第一期不得保存服务通讯录。
- 第一期不处理 AP2、E2EE、群聊或多轮 session 同步。

## 命令式入口

在本 skill 目录中运行：

```bash
python3 scripts/anp_client.py whoami
python3 scripts/anp_client.py serve-did
python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
python3 scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好"
```

## 自然语言入口

当用户说“通过 ANP 调用 http://127.0.0.1:8900 的服务智能体，问它‘你好’”，等价命令是：

```bash
python3 scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好"
```

当用户说“发现 http://127.0.0.1:8900 的 ANP 服务智能体”，等价命令是：

```bash
python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
```

当用户提供 `/agent/ad.json` URL 时，使用 `--ad-url` 而不是 `--endpoint`。

## 安全规则

- 只允许 loopback HTTP 或 HTTPS endpoint。
- 不要打印私钥内容。
- `serve-did` 仅用于本地开发、测试和 E2E；生产部署应按 DID WBA HTTPS 规则托管个人智能体 DID 文档。
```

- [ ] **Step 6: Write initial README**

Create `clients/anp-client/README.md`:

```markdown
# ANP Client Skill

`anp-client` 是安装在个人智能体中的通用客户端 skill，用于通过 ANP DID WBA 签名调用安装 Hermes `anp-agent` plugin 的服务智能体。

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

## 最小本地流程

```bash
python3 scripts/anp_client.py whoami
python3 scripts/anp_client.py serve-did
```

在本地服务智能体启动环境中设置：

```bash
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
export ANP_ALLOW_ALL_USERS=1
```

发现服务智能体：

```bash
python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
```

发送 chat：

```bash
python3 scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好"
```

## 边界

第一期只支持直接 URL、发现和 `chat`。不支持 `hermes.tool.*`、通讯录、AP2、E2EE、群聊或多轮 session 同步。

默认个人智能体 DID 为本地开发用 `did:wba:localhost...`。Phase 1 signed `chat` 验收只承诺同机 loopback 服务智能体；HTTPS endpoint 虽然通过传输安全校验，但远程服务通常无法解析该 localhost DID。生产/跨机器调用需要后续提供公开 DID 文档托管或显式 hostname 初始化能力。
```

- [ ] **Step 8: Run skeleton verification**

Run:

```bash
python3 clients/anp-client/scripts/anp_client.py --help
python3 -m pytest clients/anp-client/tests -q
```

Expected:

```text
usage: anp_client.py ...
no tests ran
```

`pytest` may return exit code 5 when no tests exist. Treat exit code 5 as expected only for this skeleton step.

- [ ] **Step 9: Commit**

If commit authorization exists:

```bash
git add clients/anp-client
git commit -m "feat: 新增 ANP client skill 骨架"
```

Expected: commit created with only `clients/anp-client` skeleton files.

---

### Task 2: DID Identity Management

**Files:**
- Modify: `clients/anp-client/scripts/did_identity.py`
- Test: `clients/anp-client/tests/test_identity.py`

**Interfaces:**
- Consumes: `anp.authentication.create_did_wba_document`.
- Produces:
  - `class IdentityError(RuntimeError)`
  - `@dataclass(frozen=True) class CallerIdentity`
  - `client_home() -> Path`
  - `load_or_create_identity(home: Path | None = None) -> CallerIdentity`
  - `load_identity(home: Path | None = None) -> CallerIdentity`

- [ ] **Step 1: Write failing identity tests**

Create `clients/anp-client/tests/test_identity.py`:

```python
"""个人智能体 DID WBA 身份测试。"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

from did_identity import (
    IdentityError,
    client_home as resolve_client_home,
    load_identity,
    load_or_create_identity,
)


def test_client_home_uses_anp_client_home(client_home: Path) -> None:
    assert resolve_client_home() == client_home
    assert resolve_client_home().name == "anp-client-home"


def test_load_or_create_identity_creates_files(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)

    assert identity.did.startswith("did:wba:")
    assert identity.did_path == client_home / "did.json"
    assert identity.key_path == client_home / "private_key.pem"
    assert identity.did_path.exists()
    assert identity.key_path.exists()
    assert identity.did_document["id"] == identity.did
    assert "keyAgreement" not in identity.did_document


def test_load_or_create_identity_reuses_existing_identity(client_home: Path) -> None:
    first = load_or_create_identity(client_home)
    second = load_or_create_identity(client_home)

    assert second.did == first.did
    assert second.did_document == first.did_document


def test_private_key_permission_is_0600(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)

    mode = stat.S_IMODE(identity.key_path.stat().st_mode)
    assert mode == 0o600


def test_load_identity_fails_when_no_identity_exists(client_home: Path) -> None:
    with pytest.raises(IdentityError, match="未找到个人智能体身份"):
        load_identity(client_home)


def test_load_or_create_fails_when_only_did_exists(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text('{"id":"did:wba:localhost:agent:e1_missing"}', encoding="utf-8")

    with pytest.raises(IdentityError, match="身份文件不完整"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_did_json_is_invalid(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text("not-json", encoding="utf-8")
    (client_home / "private_key.pem").write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_did_document_has_no_id(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text(json.dumps({"not_id": "x"}), encoding="utf-8")
    (client_home / "private_key.pem").write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档缺少 id"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_private_key_pem_is_invalid(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)
    identity.key_path.write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="私钥 PEM 无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_authentication_is_missing(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)
    doc = dict(identity.did_document)
    doc.pop("authentication", None)
    identity.did_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档缺少 authentication"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_private_key_does_not_match_did_document(client_home: Path, tmp_path: Path) -> None:
    first = load_or_create_identity(client_home)
    second_home = tmp_path / "second-home"
    second = load_or_create_identity(second_home)
    shutil.copyfile(second.key_path, first.key_path)

    with pytest.raises(IdentityError, match="私钥与 DID 文档不匹配"):
        load_or_create_identity(client_home)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_identity.py -q
```

Expected: FAIL because `CallerIdentity` and identity functions are not implemented.

- [ ] **Step 3: Implement identity module**

Replace `clients/anp-client/scripts/did_identity.py` with:

```python
"""个人智能体 DID WBA 身份管理。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base58
from anp.authentication import create_did_wba_document
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_DEFAULT_HOME = Path.home() / ".anp-client"
_DID_FILE = "did.json"
_KEY_FILE = "private_key.pem"
_PRIVATE_KEY_MODE = 0o600
_PUBLIC_FILE_MODE = 0o644
_ED25519_MULTIKEY_PREFIX = b"\xed\x01"


class IdentityError(RuntimeError):
    """个人智能体身份无法创建或加载。"""


@dataclass(frozen=True)
class CallerIdentity:
    """个人智能体 DID WBA 身份。"""

    did: str
    did_document: dict[str, Any]
    did_path: Path
    key_path: Path


def client_home() -> Path:
    """返回个人智能体身份目录。"""
    configured = os.environ.get("ANP_CLIENT_HOME")
    if configured:
        return Path(configured).expanduser()
    return _DEFAULT_HOME


def load_or_create_identity(home: Path | None = None) -> CallerIdentity:
    """加载已有身份；如果身份完全不存在则创建。"""
    root = home or client_home()
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE

    if did_path.exists() and key_path.exists():
        return _load_from_paths(did_path, key_path)
    if did_path.exists() or key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    return _create_identity(root)


def load_identity(home: Path | None = None) -> CallerIdentity:
    """只加载已有身份，不自动创建。"""
    root = home or client_home()
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE
    if not did_path.exists() and not key_path.exists():
        raise IdentityError(f"未找到个人智能体身份: {root}")
    if not did_path.exists() or not key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    return _load_from_paths(did_path, key_path)


def _atomic_write_text(path: Path, text: str, mode: int) -> None:
    """以指定权限原子写入文本文件。"""
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as file:
            file.write(text)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    """以指定权限原子写入二进制文件。"""
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as file:
            file.write(data)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


def _create_identity(root: Path) -> CallerIdentity:
    """创建新的 DID WBA 身份。"""
    root.mkdir(parents=True, exist_ok=True)
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE
    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
        enable_e2ee=False,
    )
    auth_key = keys.get("key-1")
    if not auth_key:
        raise IdentityError("DID 文档未生成 key-1 认证密钥")
    private_key_pem = auth_key[0]
    _atomic_write_text(did_path, json.dumps(did_document, indent=2, ensure_ascii=False), _PUBLIC_FILE_MODE)
    _atomic_write_bytes(key_path, private_key_pem, _PRIVATE_KEY_MODE)
    return _load_from_paths(did_path, key_path)


def _load_from_paths(did_path: Path, key_path: Path) -> CallerIdentity:
    """从文件加载 DID WBA 身份。"""
    try:
        did_document = json.loads(did_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IdentityError(f"DID 文档无法解析: {did_path}") from exc
    if not isinstance(did_document, dict):
        raise IdentityError(f"DID 文档必须是 JSON object: {did_path}")
    did = did_document.get("id")
    if not isinstance(did, str) or not did:
        raise IdentityError(f"DID 文档缺少 id: {did_path}")
    if not key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    private_key = _load_private_key(key_path)
    _validate_did_document_key_match(did_document, private_key, did_path, key_path)
    _chmod_private_key(key_path)
    return CallerIdentity(did=did, did_document=did_document, did_path=did_path, key_path=key_path)


def _load_private_key(key_path: Path) -> Ed25519PrivateKey:
    """解析 Ed25519 私钥 PEM。"""
    try:
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except ValueError as exc:
        raise IdentityError(f"私钥 PEM 无法解析: {key_path}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise IdentityError(f"私钥不是 Ed25519: {key_path}")
    return key


def _authentication_method_id(did_document: dict[str, Any], did_path: Path) -> str:
    """返回 DID 文档授权的认证 verification method id。"""
    authentication = did_document.get("authentication")
    if not isinstance(authentication, list) or not authentication:
        raise IdentityError(f"DID 文档缺少 authentication: {did_path}")
    first = authentication[0]
    if not isinstance(first, str) or not first:
        raise IdentityError(f"DID 文档 authentication 格式无效: {did_path}")
    return first


def _public_key_multibase(did_document: dict[str, Any], method_id: str, did_path: Path) -> str:
    """从 verificationMethod 中取出认证公钥。"""
    methods = did_document.get("verificationMethod")
    if not isinstance(methods, list):
        raise IdentityError(f"DID 文档缺少 verificationMethod: {did_path}")
    for method in methods:
        if isinstance(method, dict) and method.get("id") == method_id:
            value = method.get("publicKeyMultibase")
            if isinstance(value, str) and value:
                return value
            raise IdentityError(f"DID 文档认证方法缺少 publicKeyMultibase: {did_path}")
    raise IdentityError(f"DID 文档 verificationMethod 未包含 authentication: {did_path}")


def _validate_did_document_key_match(
    did_document: dict[str, Any],
    private_key: Ed25519PrivateKey,
    did_path: Path,
    key_path: Path,
) -> None:
    """确认私钥对应 DID 文档 authentication 公钥。"""
    method_id = _authentication_method_id(did_document, did_path)
    multibase_value = _public_key_multibase(did_document, method_id, did_path)
    if not multibase_value.startswith("z"):
        raise IdentityError(f"DID 文档认证公钥不是 base58btc Multikey: {did_path}")
    try:
        decoded = base58.b58decode(multibase_value[1:])
    except ValueError as exc:
        raise IdentityError(f"DID 文档认证公钥无法解析: {did_path}") from exc
    if not decoded.startswith(_ED25519_MULTIKEY_PREFIX):
        raise IdentityError(f"DID 文档认证公钥不是 Ed25519 Multikey: {did_path}")
    did_public_bytes = decoded[len(_ED25519_MULTIKEY_PREFIX) :]
    private_public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if did_public_bytes != private_public_bytes:
        raise IdentityError(f"私钥与 DID 文档不匹配: {key_path}")


def _chmod_private_key(key_path: Path) -> None:
    """确保私钥文件仅所有者可读写。"""
    key_path.chmod(_PRIVATE_KEY_MODE)
```

- [ ] **Step 4: Run identity tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_identity.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/scripts/did_identity.py clients/anp-client/tests/test_identity.py
git commit -m "feat: 实现个人智能体 DID 身份管理"
```

Expected: commit contains only identity module and tests.

---

### Task 3: DID Document Server and Basic CLI Commands

**Files:**
- Modify: `clients/anp-client/scripts/did_server.py`
- Modify: `clients/anp-client/scripts/anp_client.py`
- Test: `clients/anp-client/tests/test_cli.py`

**Interfaces:**
- Consumes: `CallerIdentity`, `load_or_create_identity()` from Task 2.
- Produces:
  - `did_document_route(did: str) -> str`
  - `is_loopback_host(host: str) -> bool`
  - `format_url_host(host: str) -> str`
  - `async serve_did_document(identity: CallerIdentity, host: str = "127.0.0.1", port: int = 18900) -> int`
  - CLI `whoami` and `serve-did` behavior.

- [ ] **Step 1: Write failing CLI/server tests**

Create `clients/anp-client/tests/test_cli.py`:

```python
"""anp-client CLI 基础命令测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from did_identity import load_or_create_identity
from did_server import did_document_route, format_url_host, is_loopback_host

CLIENT_ROOT = Path(__file__).resolve().parents[1]
CLI = CLIENT_ROOT / "scripts" / "anp_client.py"


def run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_did_document_route(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)
    route = did_document_route(identity.did)

    assert route.startswith("/agent/e1_")
    assert route.endswith("/did.json")


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_is_loopback_host_accepts_loopback(host: str) -> None:
    assert is_loopback_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.2", "example.com"])
def test_is_loopback_host_rejects_non_loopback(host: str) -> None:
    assert not is_loopback_host(host)


def test_format_url_host_wraps_ipv6_loopback() -> None:
    assert format_url_host("::1") == "[::1]"
    assert format_url_host("127.0.0.1") == "127.0.0.1"


def test_serve_did_check_only_accepts_ipv6_loopback(client_home: Path) -> None:
    env = dict(**__import__("os").environ, ANP_CLIENT_HOME=str(client_home), ANP_DID_SERVER_HOST="::1")
    result = run_cli(["serve-did", "--check-only"], env=env)

    assert result.returncode == 0
    assert "serve-did 配置检查通过" in result.stdout


def test_whoami_creates_identity(client_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = dict(**__import__("os").environ, ANP_CLIENT_HOME=str(client_home))
    result = run_cli(["whoami"], env=env)

    assert result.returncode == 0
    assert "个人智能体 DID:" in result.stdout
    assert str(client_home) in result.stdout
    assert (client_home / "did.json").exists()
    assert (client_home / "private_key.pem").exists()


def test_serve_did_rejects_non_loopback(client_home: Path) -> None:
    env = dict(**__import__("os").environ, ANP_CLIENT_HOME=str(client_home), ANP_DID_SERVER_HOST="0.0.0.0")
    result = run_cli(["serve-did", "--check-only"], env=env)

    assert result.returncode == 2
    assert "仅支持 loopback" in result.stderr
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_cli.py -q
```

Expected: FAIL because `did_server` functions and CLI command behavior are not implemented.

- [ ] **Step 3: Implement DID document server helpers**

Replace `clients/anp-client/scripts/did_server.py` with:

```python
"""个人智能体本地 DID 文档服务。"""

from __future__ import annotations

import asyncio
import signal
from ipaddress import ip_address

from aiohttp import web

from did_identity import CallerIdentity


def is_loopback_host(host: str) -> bool:
    """判断监听地址是否为 loopback。"""
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def did_document_route(did: str) -> str:
    """根据 did:wba path DID 生成 DID 文档路径。"""
    path_segments = did.split(":")[3:]
    return "/" + "/".join(path_segments) + "/did.json"


def format_url_host(host: str) -> str:
    """把监听地址格式化为可用于 URL 的 host。"""
    try:
        if ip_address(host).version == 6:
            return f"[{host}]"
    except ValueError:
        pass
    return host


async def serve_did_document(
    identity: CallerIdentity,
    host: str = "127.0.0.1",
    port: int = 18900,
) -> int:
    """启动本地 DID 文档服务，直到收到 SIGINT/SIGTERM。"""
    if not is_loopback_host(host):
        raise ValueError("serve-did 第一期仅支持 loopback 监听地址")

    route_path = did_document_route(identity.did)

    async def _handler(request: web.Request) -> web.Response:
        return web.json_response(identity.did_document)

    app = web.Application()
    app.router.add_get(route_path, _handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    addresses = runner.addresses
    if not addresses:
        await runner.cleanup()
        raise RuntimeError("DID 文档服务器未能绑定到端口")
    address = addresses[0]
    actual_host, actual_port = address[0], address[1]
    base_url = f"http://{format_url_host(str(actual_host))}:{actual_port}"

    print(f"个人智能体 DID: {identity.did}")
    print(f"DID 文档服务器: {base_url}")
    print(f"DID 文档 URL: {base_url}{route_path}")
    print("serve-did 仅用于本地开发、测试和 E2E。")
    print("生产部署应按 DID WBA HTTPS 规则托管个人智能体 DID 文档。")
    print("\n本地服务智能体可设置：")
    print(f"  export ANP_DID_RESOLVER_BASE_URL={base_url}")
    print("\n按 Ctrl+C 停止服务器。")

    stop_event = asyncio.Event()

    def _shutdown() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    await stop_event.wait()
    await runner.cleanup()
    return 0
```

- [ ] **Step 4: Implement `whoami` and safe `serve-did` CLI plumbing**

Update `clients/anp-client/scripts/anp_client.py` to include these imports and command handlers:

```python
#!/usr/bin/env python3
"""通用 ANP client skill 命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from did_identity import IdentityError, load_or_create_identity
from did_server import is_loopback_host, serve_did_document


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="anp_client.py",
        description="个人智能体调用 ANP 服务智能体的客户端工具。",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("whoami", help="显示或创建个人智能体 DID")

    serve = subcommands.add_parser("serve-did", help="启动本地 DID 文档服务")
    serve.add_argument("--host", default=os.environ.get("ANP_DID_SERVER_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("ANP_DID_SERVER_PORT", "18900")))
    serve.add_argument("--check-only", action="store_true", help="只校验配置，不启动长驻服务")

    discover = subcommands.add_parser("discover", help="发现 ANP 服务智能体")
    discover.add_argument("--endpoint")
    discover.add_argument("--ad-url")
    discover.add_argument("--json", action="store_true")

    chat = subcommands.add_parser("chat", help="向 ANP 服务智能体发送 chat")
    chat.add_argument("--endpoint")
    chat.add_argument("--ad-url")
    chat.add_argument("--message", required=True)
    chat.add_argument("--json", action="store_true")
    return parser


def _cmd_whoami() -> int:
    identity = load_or_create_identity()
    print(f"个人智能体 DID: {identity.did}")
    print(f"身份目录: {identity.did_path.parent}")
    print(f"DID 文档: {identity.did_path}")
    print(f"私钥: {identity.key_path}")
    return 0


async def _cmd_serve_did(args: argparse.Namespace) -> int:
    if not is_loopback_host(args.host):
        print("serve-did 第一期仅支持 loopback 监听地址", file=sys.stderr)
        return 2
    identity = load_or_create_identity()
    if args.check_only:
        print(f"个人智能体 DID: {identity.did}")
        print("serve-did 配置检查通过")
        return 0
    return await serve_did_document(identity, host=args.host, port=args.port)


def main() -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "whoami":
            return _cmd_whoami()
        if args.command == "serve-did":
            return asyncio.run(_cmd_serve_did(args))
        parser.error(f"命令尚未实现: {args.command}")
        return 2
    except IdentityError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/scripts/did_server.py clients/anp-client/scripts/anp_client.py clients/anp-client/tests/test_cli.py
git commit -m "feat: 实现个人智能体 DID 文档服务入口"
```

Expected: commit contains DID server and basic CLI command support.

---

### Task 4: URL Safety and Service Discovery

**Files:**
- Modify: `clients/anp-client/scripts/anp_client.py`
- Test: `clients/anp-client/tests/test_discovery.py`

**Interfaces:**
- Consumes: CLI parser from Task 3.
- Produces:
  - `class ClientError(RuntimeError)` with `exit_code: int = 2`
  - `@dataclass(frozen=True) class ServiceInfo`
  - `ensure_allowed_url(url: str) -> None`
  - `normalize_endpoint(endpoint: str) -> str`
  - `async discover_service(endpoint: str | None, ad_url: str | None, require_chat: bool = False) -> ServiceInfo`

- [ ] **Step 1: Write failing discovery tests**

Create `clients/anp-client/tests/test_discovery.py`:

```python
"""服务智能体发现测试。"""

from __future__ import annotations

import json

import pytest
from aiohttp import web

from anp_client import ClientError, discover_service, ensure_allowed_url, normalize_endpoint


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8900",
        "http://localhost:8900",
        "http://[::1]:8900",
        "https://example.com/agent/ad.json",
    ],
)
def test_ensure_allowed_url_accepts_safe_urls(url: str) -> None:
    ensure_allowed_url(url)


@pytest.mark.parametrize("url", ["http://example.com", "http://192.168.1.10:8900", "ftp://127.0.0.1"])
def test_ensure_allowed_url_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ClientError, match="只允许 loopback HTTP 或 HTTPS"):
        ensure_allowed_url(url)


def test_normalize_endpoint_strips_trailing_slash() -> None:
    assert normalize_endpoint("http://127.0.0.1:8900/") == "http://127.0.0.1:8900"


@pytest.mark.asyncio
async def test_discover_service_from_endpoint(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "测试服务智能体",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}, {"name": "anp.get_capabilities"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_service"
    assert service.name == "测试服务智能体"
    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"
    assert service.interface_url == f"{endpoint}/agent/interface.json"
    assert service.methods == ["chat", "anp.get_capabilities"]
    assert service.to_json() == {
        "service_did": "did:wba:localhost:agent:e1_service",
        "name": "测试服务智能体",
        "rpc_endpoint": f"{endpoint}/agent/rpc",
        "interface_url": f"{endpoint}/agent/interface.json",
        "methods": ["chat", "anp.get_capabilities"],
    }


@pytest.mark.asyncio
async def test_discover_rejects_non_anp_agent(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response({"protocolType": "OTHER"})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="目标不是 ANP 服务智能体"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_allows_missing_chat_for_discover(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "无 chat 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "anp.get_capabilities"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.methods == ["anp.get_capabilities"]


@pytest.mark.asyncio
async def test_discover_service_requires_chat_for_chat_calls(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "无 chat 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "anp.get_capabilities"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="服务智能体未声明 chat 方法"):
            await discover_service(endpoint=endpoint, ad_url=None, require_chat=True)
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_discover_service_from_ad_url_derives_rpc_endpoint(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    ad_url = f"{endpoint}/agent/ad.json"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "AD URL 服务",
                "did": "did:wba:localhost:agent:e1_adurl",
                "endpoint": endpoint,
                "interfaces": [{"type": "StructuredInterface", "protocol": "openrpc", "url": "/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=None, ad_url=ad_url)
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_adurl"
    assert service.rpc_endpoint == f"{endpoint}/agent/rpc"
    assert service.interface_url == f"{endpoint}/agent/interface.json"


@pytest.mark.asyncio
async def test_discover_service_selects_openrpc_interface_and_server_url(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    custom_rpc = f"{endpoint}/custom/rpc"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "自定义 RPC 服务",
                "did": "did:wba:localhost:agent:e1_custom",
                "endpoint": endpoint,
                "interfaces": [
                    {"type": "OtherInterface", "url": f"{endpoint}/wrong.json"},
                    {"type": "StructuredInterface", "protocol": "openrpc", "url": f"{endpoint}/agent/interface.json"},
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "openrpc": "1.3.2",
                "servers": [{"url": custom_rpc}],
                "methods": [{"name": "chat"}],
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        service = await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.interface_url == f"{endpoint}/agent/interface.json"
    assert service.rpc_endpoint == custom_rpc


@pytest.mark.asyncio
async def test_discover_service_reports_http_failure(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    with pytest.raises(ClientError, match="无法连接服务智能体"):
        await discover_service(endpoint=endpoint, ad_url=None)


@pytest.mark.asyncio
async def test_discover_service_does_not_follow_redirects(aiohttp_unused_port) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def redirect_handler(request: web.Request) -> web.Response:
        raise web.HTTPFound("http://example.com/agent/ad.json")

    app = web.Application()
    app.router.add_get("/agent/ad.json", redirect_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="不支持 HTTP redirect"):
            await discover_service(endpoint=endpoint, ad_url=None)
    finally:
        await runner.cleanup()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_discovery.py -q
```

Expected: FAIL because discovery helpers do not exist.

- [ ] **Step 3: Add discovery data structures and URL safety helpers**

Add to `clients/anp-client/scripts/anp_client.py` after imports:

```python
import json
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp


class ClientError(RuntimeError):
    """anp-client 可展示给用户的错误。"""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class ServiceInfo:
    """已发现的 ANP 服务智能体信息。"""

    service_did: str
    name: str
    rpc_endpoint: str
    interface_url: str
    methods: list[str]

    def to_json(self) -> dict[str, Any]:
        return {
            "service_did": self.service_did,
            "name": self.name,
            "rpc_endpoint": self.rpc_endpoint,
            "interface_url": self.interface_url,
            "methods": self.methods,
        }


def normalize_endpoint(endpoint: str) -> str:
    """规范化 endpoint。"""
    return endpoint.rstrip("/")


def ensure_allowed_url(url: str) -> None:
    """只允许 loopback HTTP 与 HTTPS。"""
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme != "http":
        raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")
    host = parsed.hostname or ""
    if host == "localhost":
        return
    try:
        if ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ClientError("只允许 loopback HTTP 或 HTTPS endpoint")
```

- [ ] **Step 4: Add discovery implementation**

Add to `clients/anp-client/scripts/anp_client.py`:

```python
async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    """读取 JSON object。"""
    ensure_allowed_url(url)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False) as resp:
            if 300 <= resp.status < 400:
                raise ClientError(f"不支持 HTTP redirect: {url}")
            data = await resp.json()
    except aiohttp.ClientError as exc:
        raise ClientError(f"无法连接服务智能体: {url}") from exc
    if not isinstance(data, dict):
        raise ClientError(f"响应不是 JSON object: {url}")
    return data


def _interface_url_from_ad(ad: dict[str, Any], ad_url: str, endpoint: str) -> str:
    """从 Agent Description 选择 OpenRPC interface URL。"""
    interfaces = ad.get("interfaces")
    if isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            is_openrpc = item.get("protocol") == "openrpc" or item.get("type") == "openrpc"
            if is_openrpc and isinstance(item.get("url"), str):
                return urljoin(ad_url, item["url"])
    return f"{endpoint}/agent/interface.json"


def _rpc_endpoint_from_interface(interface_doc: dict[str, Any], endpoint: str) -> str:
    """从 OpenRPC servers 中选择 RPC endpoint，缺失时回退到 Hermes 默认路径。"""
    servers = interface_doc.get("servers")
    if isinstance(servers, list):
        for server in servers:
            if isinstance(server, dict) and isinstance(server.get("url"), str):
                return urljoin(endpoint + "/", server["url"])
    return f"{endpoint}/agent/rpc"


def _methods_from_interface(interface_doc: dict[str, Any]) -> list[str]:
    methods = interface_doc.get("methods")
    if not isinstance(methods, list):
        return []
    names: list[str] = []
    for method in methods:
        if isinstance(method, dict) and isinstance(method.get("name"), str):
            names.append(method["name"])
    return names


async def discover_service(
    endpoint: str | None,
    ad_url: str | None,
    require_chat: bool = False,
) -> ServiceInfo:
    """发现服务智能体；按需确认 chat 方法存在。"""
    if bool(endpoint) == bool(ad_url):
        raise ClientError("必须且只能提供 --endpoint 或 --ad-url")

    if endpoint:
        normalized_endpoint = normalize_endpoint(endpoint)
        ensure_allowed_url(normalized_endpoint)
        resolved_ad_url = f"{normalized_endpoint}/agent/ad.json"
    else:
        resolved_ad_url = ad_url or ""
        ensure_allowed_url(resolved_ad_url)
        normalized_endpoint = ""

    async with aiohttp.ClientSession() as session:
        ad = await _fetch_json(session, resolved_ad_url)
        if ad.get("protocolType") != "ANP":
            raise ClientError("目标不是 ANP 服务智能体")

        service_did = ad.get("did") or ad.get("id")
        if not isinstance(service_did, str) or not service_did:
            raise ClientError("Agent Description 缺少服务 DID")

        name = ad.get("name") if isinstance(ad.get("name"), str) else "ANP 服务智能体"
        ad_endpoint = ad.get("endpoint")
        if not normalized_endpoint:
            if not isinstance(ad_endpoint, str) or not ad_endpoint:
                raise ClientError("Agent Description 缺少 RPC endpoint")
            normalized_endpoint = normalize_endpoint(ad_endpoint)
        ensure_allowed_url(normalized_endpoint)

        interface_url = _interface_url_from_ad(ad, resolved_ad_url, normalized_endpoint)
        ensure_allowed_url(interface_url)
        interface_doc = await _fetch_json(session, interface_url)
        rpc_endpoint = _rpc_endpoint_from_interface(interface_doc, normalized_endpoint)
        ensure_allowed_url(rpc_endpoint)
        methods = _methods_from_interface(interface_doc)
        if require_chat and "chat" not in methods:
            method_list = ", ".join(methods) if methods else "(none)"
            raise ClientError(f"服务智能体未声明 chat 方法；已发现方法: {method_list}")

        return ServiceInfo(
            service_did=service_did,
            name=name,
            rpc_endpoint=rpc_endpoint,
            interface_url=interface_url,
            methods=methods,
        )
```

- [ ] **Step 5: Wire `discover` CLI output**

Update `main()` and add handler in `anp_client.py`:

```python
async def _cmd_discover(args: argparse.Namespace) -> int:
    service = await discover_service(endpoint=args.endpoint, ad_url=args.ad_url)
    if args.json:
        print(json.dumps(service.to_json(), ensure_ascii=False))
        return 0
    print(f"服务智能体: {service.name}")
    print(f"服务 DID: {service.service_did}")
    print(f"RPC endpoint: {service.rpc_endpoint}")
    print(f"OpenRPC interface: {service.interface_url}")
    print("可用方法:")
    for method in service.methods:
        print(f"  - {method}")
    return 0
```

In `main()`, add before `parser.error(...)`:

```python
        if args.command == "discover":
            return asyncio.run(_cmd_discover(args))
```

Also catch `ClientError`:

```python
    except ClientError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
```

- [ ] **Step 6: Run discovery tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_discovery.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/scripts/anp_client.py clients/anp-client/tests/test_discovery.py
git commit -m "feat: 实现 ANP 服务智能体发现"
```

Expected: commit contains discovery logic and tests.

---

### Task 5: DID WBA Signing and Chat Flow

**Files:**
- Modify: `clients/anp-client/scripts/signing.py`
- Modify: `clients/anp-client/scripts/anp_client.py`
- Test: `clients/anp-client/tests/test_chat.py`

**Interfaces:**
- Consumes: `CallerIdentity`, `load_or_create_identity()`, `ServiceInfo`, `discover_service()`.
- Produces:
  - `build_signed_headers(identity: CallerIdentity, target_url: str, body: str) -> dict[str, str]`
  - `build_chat_body(message: str, request_id: str | None = None) -> tuple[str, str]`
  - `async chat_service(endpoint: str | None, ad_url: str | None, message: str) -> dict[str, Any]`

- [ ] **Step 1: Write failing chat tests**

Create `clients/anp-client/tests/test_chat.py`:

```python
"""chat 调用与签名测试。"""

from __future__ import annotations

import json

import pytest
from aiohttp import web

from anp_client import ClientError, build_chat_body, chat_service, format_rpc_error
from did_identity import load_or_create_identity
from signing import build_signed_headers


@pytest.mark.asyncio
async def test_build_signed_headers_adds_content_type(client_home) -> None:
    identity = load_or_create_identity(client_home)
    body = json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {"message": "你好"}, "id": "1"})

    headers = await build_signed_headers(identity, "http://127.0.0.1:8900/agent/rpc", body)

    assert headers["Content-Type"] == "application/json"
    assert "Signature" in headers
    assert "Signature-Input" in headers


def test_build_chat_body_uses_legacy_params_message() -> None:
    body, request_id = build_chat_body("你好", request_id="chat-test")
    data = json.loads(body)

    assert request_id == "chat-test"
    assert data == {
        "jsonrpc": "2.0",
        "id": "chat-test",
        "method": "chat",
        "params": {"message": "你好"},
    }


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (-32002, "请先运行 serve-did"),
        (-32001, "检查个人智能体 DID"),
        (-32003, "必须通过 chat 命令发送 DID WBA 签名请求"),
    ],
)
def test_format_rpc_error_guidance(code: int, expected: str) -> None:
    message = format_rpc_error({"code": code, "message": "错误"})
    assert expected in message


@pytest.mark.asyncio
async def test_chat_service_returns_json_result(aiohttp_unused_port, client_home) -> None:
    load_or_create_identity(client_home)
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    captured_headers: dict[str, str] = {}

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "Echo 服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        captured_headers.update(dict(request.headers))
        body = await request.json()
        return web.json_response(
            {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"response": f"收到: {body['params']['message']}"},
            }
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        result = await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()

    assert "Signature" in captured_headers
    assert "Signature-Input" in captured_headers
    assert result["service_did"] == "did:wba:localhost:agent:e1_service"
    assert result["caller_did"].startswith("did:wba:")
    assert result["http_status"] == 200
    assert result["response"] == "收到: hello"


@pytest.mark.asyncio
async def test_chat_service_reports_json_rpc_error(aiohttp_unused_port, client_home) -> None:
    load_or_create_identity(client_home)
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "认证失败服务",
                "did": "did:wba:localhost:agent:e1_service",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"jsonrpc": "2.0", "id": "x", "error": {"code": -32002, "message": "DID 文档无法解析"}}
        )

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        with pytest.raises(ClientError, match="请先运行 serve-did"):
            await chat_service(endpoint=endpoint, ad_url=None, message="hello")
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_chat_service_reports_http_failure(aiohttp_unused_port, client_home) -> None:
    load_or_create_identity(client_home)
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    with pytest.raises(ClientError, match="无法连接服务智能体"):
        await chat_service(endpoint=endpoint, ad_url=None, message="hello")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

Expected: FAIL because signing/chat helpers are not implemented.

- [ ] **Step 3: Implement signing helper**

Replace `clients/anp-client/scripts/signing.py` with:

```python
"""ANP DID WBA HTTP Signature 生成。"""

from __future__ import annotations

from anp.authentication import DIDWbaAuthHeader

from did_identity import CallerIdentity


async def build_signed_headers(
    identity: CallerIdentity,
    target_url: str,
    body: str,
) -> dict[str, str]:
    """为 JSON-RPC POST body 生成 DID WBA HTTP Signature 请求头。"""
    auth = DIDWbaAuthHeader(
        did_document_path=str(identity.did_path),
        private_key_path=str(identity.key_path),
        auth_mode="http_signatures",
    )
    headers = auth.get_auth_header(
        server_url=target_url,
        force_new=True,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=body,
    )
    headers["Content-Type"] = "application/json"
    return headers
```

- [ ] **Step 4: Implement chat helpers**

Add to `clients/anp-client/scripts/anp_client.py`:

```python
from uuid import uuid4

from signing import build_signed_headers


def build_chat_body(message: str, request_id: str | None = None) -> tuple[str, str]:
    """构造 legacy params.message JSON-RPC chat body。"""
    rpc_id = request_id or f"chat-{uuid4().hex}"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": "chat",
            "params": {"message": message},
        },
        ensure_ascii=False,
    )
    return body, rpc_id


def format_rpc_error(error: dict[str, Any]) -> str:
    """格式化 JSON-RPC error，并附加常见 DID WBA 故障提示。"""
    code = error.get("code")
    message = error.get("message", "未知错误")
    lines = [f"JSON-RPC error {code}: {message}"]
    if code == -32002:
        lines.append("请先运行 serve-did，并在本地服务智能体设置 ANP_DID_RESOLVER_BASE_URL。")
    elif code == -32001:
        lines.append("请检查个人智能体 DID、私钥、签名 body 与服务端 DID 文档解析结果是否匹配。")
    elif code == -32003:
        lines.append("必须通过 chat 命令发送 DID WBA 签名请求，而不是裸 HTTP 请求。")
    data = error.get("data")
    if data is not None:
        lines.append(f"data: {data}")
    return "\n".join(lines)


async def chat_service(endpoint: str | None, ad_url: str | None, message: str) -> dict[str, Any]:
    """发现服务智能体并发送 DID WBA 签名 chat。"""
    identity = load_or_create_identity()
    service = await discover_service(endpoint=endpoint, ad_url=ad_url, require_chat=True)
    body, rpc_id = build_chat_body(message)
    headers = await build_signed_headers(identity, service.rpc_endpoint, body)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                service.rpc_endpoint,
                data=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
                allow_redirects=False,
            ) as resp:
                if 300 <= resp.status < 400:
                    raise ClientError(f"不支持 HTTP redirect: {service.rpc_endpoint}")
                response_body = await resp.json()
                http_status = resp.status
    except aiohttp.ClientError as exc:
        raise ClientError(f"无法连接服务智能体: {service.rpc_endpoint}") from exc

    if not isinstance(response_body, dict):
        raise ClientError("服务智能体响应不是 JSON object")
    if response_body.get("error") is not None:
        error = response_body["error"]
        if isinstance(error, dict):
            raise ClientError(format_rpc_error(error), exit_code=1)
        raise ClientError("服务智能体返回无法解析的 JSON-RPC error", exit_code=1)
    result = response_body.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise ClientError("服务智能体响应缺少 result.response", exit_code=1)

    return {
        "service_did": service.service_did,
        "caller_did": identity.did,
        "http_status": http_status,
        "jsonrpc_id": response_body.get("id", rpc_id),
        "response": result["response"],
    }
```

- [ ] **Step 5: Wire `chat` CLI output**

Add to `clients/anp-client/scripts/anp_client.py`:

```python
async def _cmd_chat(args: argparse.Namespace) -> int:
    result = await chat_service(endpoint=args.endpoint, ad_url=args.ad_url, message=args.message)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return 0
    print(f"服务 DID: {result['service_did']}")
    print(f"个人智能体 DID: {result['caller_did']}")
    print("\n回复:")
    print(result["response"])
    return 0
```

In `main()`, add before `parser.error(...)`:

```python
        if args.command == "chat":
            return asyncio.run(_cmd_chat(args))
```

- [ ] **Step 6: Run chat tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/scripts/signing.py clients/anp-client/scripts/anp_client.py clients/anp-client/tests/test_chat.py
git commit -m "feat: 实现 DID WBA 签名 chat 调用"
```

Expected: commit contains signing/chat implementation and tests.

---

### Task 6: Natural-Language Examples and Documentation

**Files:**
- Modify: `clients/anp-client/scripts/anp_client.py`
- Modify: `clients/anp-client/SKILL.md`
- Modify: `clients/anp-client/README.md`
- Test: `clients/anp-client/tests/test_natural_language_examples.py`

**Interfaces:**
- Consumes: CLI command contract from Tasks 3-5.
- Produces:
  - `normalize_natural_language(text: str) -> dict[str, str]`
  - `SKILL.md` examples matching fixture assertions.

- [ ] **Step 1: Write failing natural-language tests**

Create `clients/anp-client/tests/test_natural_language_examples.py`:

```python
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
            {"action": "chat", "ad_url": "http://127.0.0.1:8900/agent/ad.json", "message": "你好"},
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
def test_normalize_natural_language_examples(text: str, expected: dict[str, str]) -> None:
    assert normalize_natural_language(text) == expected


def test_normalize_natural_language_rejects_missing_url() -> None:
    with pytest.raises(ClientError, match="未找到 ANP 服务 URL"):
        normalize_natural_language("问它你好")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_natural_language_examples.py -q
```

Expected: FAIL because `normalize_natural_language()` is not implemented.

- [ ] **Step 3: Implement deterministic normalizer**

Add to `clients/anp-client/scripts/anp_client.py`:

```python
import re

_URL_RE = re.compile(r"https?://[^\s，,。'\"“”]+")
_QUOTED_MESSAGE_RE = re.compile(r"[问问它]+[：:]?[“\"](?P<message>.+?)[”\"]")
_SEND_MESSAGE_RE = re.compile(r"(?:发送|send)[：:\s]+(?P<message>.+)$", re.IGNORECASE)


def normalize_natural_language(text: str) -> dict[str, str]:
    """将 SKILL.md 承诺的固定自然语言样例规范化为命令参数。"""
    stripped = text.strip()
    match = _URL_RE.search(stripped)
    if not match:
        raise ClientError("未找到 ANP 服务 URL")
    url = match.group(0).rstrip("，,。")
    url_key = "ad_url" if url.endswith("/agent/ad.json") else "endpoint"

    is_discover = "发现" in stripped or "discover" in stripped.lower()
    has_chat_intent = any(keyword in stripped for keyword in ("问它", "发送", "chat"))
    if is_discover and not has_chat_intent:
        return {"action": "discover", url_key: url}

    message_match = _QUOTED_MESSAGE_RE.search(stripped)
    if message_match:
        message = message_match.group("message").strip()
    else:
        send_match = _SEND_MESSAGE_RE.search(stripped)
        if not send_match:
            raise ClientError("未找到要发送的消息")
        message = send_match.group("message").strip().strip("。")
    return {"action": "chat", url_key: url, "message": message}
```

- [ ] **Step 4: Update `SKILL.md` examples to match tests**

Ensure `clients/anp-client/SKILL.md` includes these exact examples:

```markdown
## 自然语言样例

| 用户表达 | 等价参数 |
| --- | --- |
| `通过 ANP 调用 http://127.0.0.1:8900 的服务智能体，问它“你好”` | `action=chat endpoint=http://127.0.0.1:8900 message=你好` |
| `请连接 http://127.0.0.1:8900/agent/ad.json 并发送：你好` | `action=chat ad_url=http://127.0.0.1:8900/agent/ad.json message=你好` |
| `用 ANP client 向 http://127.0.0.1:8900 发送 hello` | `action=chat endpoint=http://127.0.0.1:8900 message=hello` |
| `发现 http://127.0.0.1:8900 的 ANP 服务智能体` | `action=discover endpoint=http://127.0.0.1:8900` |
```

- [ ] **Step 5: Update README troubleshooting and boundary text**

Append to `clients/anp-client/README.md`:

```markdown
## 故障排查

### DID 文档无法解析（`-32002`）

先运行：

```bash
python3 scripts/anp_client.py serve-did
```

然后确保本地服务智能体启动环境中设置：

```bash
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

### 签名无效（`-32001`）

检查 `~/.anp-client/did.json` 与 `~/.anp-client/private_key.pem` 是否匹配，确认请求 body 在签名后没有被修改。

### 缺少认证头（`-32003`）

必须通过 `python3 scripts/anp_client.py chat ...` 发送 DID WBA 签名请求，不要直接用裸 HTTP POST 调用 `/agent/rpc`。

### endpoint 被拒绝

第一期只允许 loopback HTTP 和 HTTPS：

- `http://127.0.0.1:<port>`
- `http://localhost:<port>`
- `http://[::1]:<port>`
- `https://<host>`

`http://example.com`、局域网 IP 和公网明文 HTTP 会被拒绝。

### `serve-did` 的生产边界

`serve-did` 仅用于本地开发、测试和 E2E。默认生成的个人智能体 DID 为 `did:wba:localhost...`，同机服务智能体可通过 `ANP_DID_RESOLVER_BASE_URL` 解析。HTTPS endpoint 虽然通过传输安全策略校验，但远程服务通常无法解析本机 localhost DID；生产/跨机器调用需要后续提供公开 DID 文档托管或显式 hostname 初始化能力。
```

- [ ] **Step 6: Run natural-language and docs-adjacent tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_natural_language_examples.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/scripts/anp_client.py clients/anp-client/SKILL.md clients/anp-client/README.md clients/anp-client/tests/test_natural_language_examples.py
git commit -m "feat: 增加 ANP client 自然语言样例契约"
```

Expected: commit contains deterministic natural-language normalizer, docs, and tests.

---

### Task 7: Integration and E2E Coverage

**Files:**
- Modify: `clients/anp-client/tests/test_discovery.py`
- Modify: `clients/anp-client/tests/test_chat.py`
- Create: `plugins/anp-agent/tests/e2e/test_anp_client_skill.py`

**Interfaces:**
- Consumes: all CLI modules from Tasks 2-6.
- Produces:
  - Mock aiohttp integration tests for `discover --json` and `chat --json`.
  - Real Hermes E2E test using `anp-client` CLI.

- [ ] **Step 1: Add CLI subprocess integration test for `discover --json`**

Append to `clients/anp-client/tests/test_discovery.py`:

```python
import asyncio
import os
import sys
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[1]
CLI = CLIENT_ROOT / "scripts" / "anp_client.py"


async def run_cli_async(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """在 async 测试中运行 CLI，避免阻塞 aiohttp mock server 的 event loop。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(CLI),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@pytest.mark.asyncio
async def test_discover_cli_json_output(aiohttp_unused_port, client_home: Path) -> None:
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "CLI 服务",
                "did": "did:wba:localhost:agent:e1_cli",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))
        returncode, stdout, stderr = await run_cli_async(
            ["discover", "--endpoint", endpoint, "--json"],
            env=env,
        )
    finally:
        await runner.cleanup()

    assert returncode == 0, stderr
    data = json.loads(stdout)
    assert data["service_did"] == "did:wba:localhost:agent:e1_cli"
    assert data["name"] == "CLI 服务"
    assert data["rpc_endpoint"] == f"{endpoint}/agent/rpc"
    assert data["interface_url"] == f"{endpoint}/agent/interface.json"
    assert data["methods"] == ["chat"]
    assert not (client_home / "did.json").exists()
    assert not (client_home / "private_key.pem").exists()
```

- [ ] **Step 2: Add CLI subprocess integration test for `chat --json`**

Append to `clients/anp-client/tests/test_chat.py`:

```python
import asyncio
import os
import sys
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[1]
CLI = CLIENT_ROOT / "scripts" / "anp_client.py"


async def run_cli_async(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """在 async 测试中运行 CLI，避免阻塞 aiohttp mock server 的 event loop。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(CLI),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@pytest.mark.asyncio
async def test_chat_cli_json_output(aiohttp_unused_port, client_home: Path) -> None:
    load_or_create_identity(client_home)
    port = aiohttp_unused_port()
    endpoint = f"http://127.0.0.1:{port}"
    captured_headers: dict[str, str] = {}

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "CLI Echo",
                "did": "did:wba:localhost:agent:e1_cli_echo",
                "endpoint": endpoint,
                "interfaces": [{"type": "openrpc", "url": f"{endpoint}/agent/interface.json"}],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"methods": [{"name": "chat"}]})

    async def rpc_handler(request: web.Request) -> web.Response:
        captured_headers.update(dict(request.headers))
        body = await request.json()
        return web.json_response({"jsonrpc": "2.0", "id": body["id"], "result": {"response": "pong"}})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    app.router.add_post("/agent/rpc", rpc_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    try:
        env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))
        returncode, stdout, stderr = await run_cli_async(
            ["chat", "--endpoint", endpoint, "--message", "ping", "--json"],
            env=env,
        )
    finally:
        await runner.cleanup()

    assert returncode == 0, stderr
    assert "Signature" in captured_headers
    data = json.loads(stdout)
    assert data["service_did"] == "did:wba:localhost:agent:e1_cli_echo"
    assert data["response"] == "pong"
```

- [ ] **Step 3: Run integration tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_discovery.py clients/anp-client/tests/test_chat.py -q
```

Expected: PASS.

- [ ] **Step 4: Write real Hermes E2E test**

Create `plugins/anp-agent/tests/e2e/test_anp_client_skill.py`:

```python
"""anp-client skill 调用真实 Hermes ANP 服务智能体的 E2E。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest


async def run_cli_async(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """运行 anp-client CLI，避免阻塞 pytest event loop 中的 DID/mock 服务。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@pytest.mark.asyncio
async def test_anp_client_skill_discovers_and_chats_with_hermes(
    hermes_gateway,
    anp_caller_identity,
):
    """anp-client CLI 应能发现服务智能体并通过 chat 获得回复。"""
    repo_root = Path(__file__).resolve().parents[4]
    client_script = repo_root / "clients" / "anp-client" / "scripts" / "anp_client.py"
    endpoint = hermes_gateway["endpoint"]
    client_home = Path(anp_caller_identity["did_path"]).parent
    env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))

    discover_returncode, discover_stdout, discover_stderr = await run_cli_async(
        [str(client_script), "discover", "--endpoint", endpoint, "--json"],
        env=env,
    )
    assert discover_returncode == 0, discover_stderr
    discover_data = json.loads(discover_stdout)
    assert "chat" in discover_data["methods"]
    assert discover_data["service_did"].startswith("did:wba:")

    chat_returncode, chat_stdout, chat_stderr = await run_cli_async(
        [
            str(client_script),
            "chat",
            "--endpoint",
            endpoint,
            "--message",
            "hello-anp-client-skill",
            "--json",
        ],
        env=env,
    )
    assert chat_returncode == 0, chat_stderr
    chat_data = json.loads(chat_stdout)
    assert chat_data["http_status"] == 200
    assert "hello-anp-client-skill" in chat_data["response"]
```

- [ ] **Step 5: Run client unit/integration tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests -q
```

Expected: all client skill tests PASS.

- [ ] **Step 6: Run existing plugin focused tests**

Run:

```bash
cd plugins/anp-agent && python3 -m pytest tests/test_integration.py tests/test_server.py -q
```

Expected: PASS. If this command fails because dependencies are missing, install with:

```bash
cd plugins/anp-agent && python3 -m pip install -e ".[test,dev]"
```

Then rerun the focused tests.

- [ ] **Step 7: Run E2E echo test including new client skill test**

Run:

```bash
cd plugins/anp-agent && python3 -m pytest tests/e2e/test_echo.py tests/e2e/test_anp_client_skill.py -v --run-e2e
```

Expected: both E2E tests PASS. If Hermes is not installed in the execution environment, report the skipped or failed environment precondition with the exact error output.

- [ ] **Step 8: Commit**

If commit authorization exists:

```bash
git add clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
git commit -m "test: 覆盖 ANP client skill 集成与 E2E"
```

Expected: commit contains integration and E2E tests.

---

### Task 8: Quality Gate, OpenSpec Verification, and Packaging Check

**Files:**
- Modify as needed: `clients/anp-client/SKILL.md`
- Modify as needed: `clients/anp-client/README.md`
- Modify as needed: `openspec/changes/add-anp-client-skill/tasks.md`

**Interfaces:**
- Consumes: completed client skill implementation and tests.
- Produces:
  - Verified test/lint/OpenSpec output.
  - Updated OpenSpec task checkboxes after successful implementation.

- [ ] **Step 1: Install client skill verification dependencies**

Run:

```bash
python3 -m pip install -r clients/anp-client/requirements-dev.txt
```

Expected: runtime, test, formatting, and lint dependencies are installed for local verification.

- [ ] **Step 2: Run Python formatting check**

Run:

```bash
black --check clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
```

Expected: PASS. If it fails, run:

```bash
black clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
```

Then rerun `black --check`.

- [ ] **Step 3: Run ruff**

Run:

```bash
ruff check clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
```

Expected: PASS. If import sorting fails, run:

```bash
ruff check --fix clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
```

Then rerun `ruff check`.

- [ ] **Step 4: Run full client test suite**

Run:

```bash
python3 -m pytest clients/anp-client/tests -q
```

Expected: PASS.

- [ ] **Step 5: Run plugin coverage gate**

Run:

```bash
cd plugins/anp-agent && python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

Expected: PASS with coverage >= 85%.

- [ ] **Step 6: Run OpenSpec validation**

Run:

```bash
openspec validate add-anp-client-skill --type change
openspec validate --all
```

Expected:

```text
Change 'add-anp-client-skill' is valid
Totals: ... passed, 0 failed
```

- [ ] **Step 7: Check self-contained package boundaries**

Run:

```bash
find clients/anp-client -type l -print
find clients/anp-client -name 'did.json' -o -name 'private_key.pem' -o -name '*.tmp' -o -name '*.bak*'
grep -R "/home/peter/anp-hermes" -n clients/anp-client || true
```

Expected:

```text
# first command prints nothing
# second command prints nothing
# grep prints nothing
```

- [ ] **Step 8: Mark OpenSpec tasks complete only after verification passes**

Edit `openspec/changes/add-anp-client-skill/tasks.md` and change each completed implementation checkbox from `- [ ]` to `- [x]`. Do not mark a task complete unless its verification command passed or the failure is an explicitly reported environment precondition.

- [ ] **Step 9: Run OpenSpec task verification**

Run:

```bash
openspec instructions apply --change "add-anp-client-skill" --json
openspec validate add-anp-client-skill --type change
```

Expected: `progress.remaining` is `0`, and the change validates.

- [ ] **Step 10: Commit final verified state**

If commit authorization exists:

```bash
git add clients/anp-client plugins/anp-agent/tests/e2e/test_anp_client_skill.py openspec/changes/add-anp-client-skill/tasks.md
git commit -m "test: 验证 ANP client skill 变更"
```

Expected: final implementation commit contains completed task checkboxes and verified code/docs/tests.

---

## Self-Review

### Spec Coverage

- 自包含 skill：Tasks 1 and 8 create and verify `clients/anp-client/` has no symlinks, secrets, or absolute repo dependencies.
- 命令式入口：Tasks 3-5 implement `whoami`、`serve-did`、`discover`、`chat`.
- DID 身份管理：Task 2 covers generation, reuse, `ANP_CLIENT_HOME`, permissions, damaged identity errors, and the decision that `discover` remains a read-only flow that does not create identity files.
- 本地 DID 文档服务：Task 3 covers route generation, loopback enforcement, local-only messaging, and resolver env output.
- 服务发现：Task 4 covers endpoint/ad-url discovery, ANP validation, service DID, interface URL, methods, missing `chat`, and `discover --json`.
- DID WBA signed chat：Task 5 covers body construction, signing, POST `/agent/rpc`, JSON output, success and error handling.
- endpoint 安全策略：Task 4 tests loopback HTTP, HTTPS, and non-loopback HTTP rejection.
- 自然语言样例解析：Task 6 implements deterministic normalizer and tests the fixed examples.
- 一期能力边界：Task 1 and Task 6 document no `hermes.tool.*`, no remote tool execution, no address book, no AP2/E2EE/group/session sync; Task 8 packaging check prevents runtime secrets.
- 测试覆盖：Task 7 adds mock integration and real Hermes E2E; Task 8 runs full quality gates.

### Placeholder Scan

No `TBD`, `TODO`, “implement later”, or unspecified “add validation” steps remain. Each implementation task includes exact file paths, function names, test commands, and expected results.

### Type Consistency

- `CallerIdentity` is defined in Task 2 and consumed by `did_server.py` and `signing.py` in Tasks 3 and 5.
- `ServiceInfo.to_json()` returns the exact `discover --json` keys from the spec: `service_did`、`name`、`rpc_endpoint`、`interface_url`、`methods`.
- `chat_service()` returns the exact `chat --json` keys from the spec: `service_did`、`caller_did`、`http_status`、`jsonrpc_id`、`response`.
- `normalize_natural_language()` returns `action` plus either `endpoint` or `ad_url`, and `message` for chat actions.

## Execution Handoff

Plan complete. Use either subagent-driven or inline execution after user approval. Do not start implementation until the user confirms execution mode.

## GSTACK REVIEW REPORT

### Review Status

- Reviewed change: `openspec/changes/add-anp-client-skill`
- Reviewed plan: `docs/superpowers/plans/2026-07-09-add-anp-client-skill.md`
- Review mode: FULL_REVIEW
- OpenSpec validation after review edits: PASS
  - `openspec validate add-anp-client-skill --type change`
  - `openspec validate --all` → 16 passed, 0 failed
- Test plan artifact: `~/.gstack/projects/anp-hermes/peter-master-eng-review-test-plan-20260709-103215.md`
- Implementation task artifact: `~/.gstack/projects/anp-hermes/tasks-eng-review-20260709-111747.jsonl`

### Decisions Applied During Review

- D3: `discover` remains read-only and must not create `did.json` / `private_key.pem`.
- D4: Distribution wording changed from ClawHub-only to a generic skill install bundle boundary.
- D6: Fixed the `client_home` test shadowing bug by importing `client_home` as `resolve_client_home`.
- D7: Split `discover` and `chat` validation: `discover` lists methods even without `chat`; `chat` requires `chat`.
- D9: Added a local `aiohttp_unused_port` fixture backed by `aiohttp.test_utils.unused_port`.
- D10: Added coverage for `discover --ad-url`, HTTP/JSON-RPC errors, and package boundary checks.
- D13-D22: Incorporated outside-voice findings: async subprocess test harness, redirect rejection, Phase 1 localhost DID boundary, full identity validation, no Phase 1 E2EE keyAgreement, atomic identity writes, OpenRPC server URL parsing, IPv6 URL formatting, `ClientError` test import, and `requirements-dev.txt`.
- D23: Added `TODO-5` for future public DID hosting / hostname initialization.

### NOT in Scope

- `hermes.tool.*` RPC invocation — deliberately excluded from Phase 1 until caller DID authorization and risk policy are separately designed.
- Service address book / aliases / multi-service routing — deferred to avoid turning the MVP into service registry work.
- AP2, E2EE, group chat, DTR, Portal, Mediator, and multi-round session sync — existing TODOs track future protocol expansion.
- Public/cross-machine personal-agent DID hosting — now explicitly deferred as `TODO-5`; Phase 1 signed `chat` only promises same-machine loopback service agents.
- Publishing automation for a hosted skill marketplace — package boundary is defined and testable, but release pipeline is not part of this change.

### What Already Exists

- `scripts/start_did_server.py` — prototype for caller DID generation and local DID document serving; the plan reuses its flow but productizes it under `clients/anp-client/`.
- `scripts/anp_chat_client.py` — prototype for discovery + signed legacy `params.message` chat; the plan reuses the protocol shape.
- `plugins/anp-agent/tests/helpers/signing.py` — known-good `DIDWbaAuthHeader` usage; the plan mirrors this in `scripts/signing.py`.
- `plugins/anp-agent/anp_agent/identity.py` — atomic write pattern for identity files; the plan now copies this pattern for client identity.
- `plugins/anp-agent/tests/e2e/conftest.py` and `test_echo.py` — existing Hermes gateway E2E harness; the plan adds an anp-client skill E2E alongside it.

### Test Coverage Diagram

```text
CODE PATHS                                                     USER FLOWS
[+] clients/anp-client/scripts/did_identity.py                  [+] First-run personal identity
  ├── [★★★ TESTED] create new identity                           ├── [★★★ TESTED] whoami creates identity
  ├── [★★★ TESTED] reuse existing identity                       ├── [★★★ TESTED] partial/damaged identity errors
  ├── [★★★ TESTED] partial/missing identity                      └── [★★★ TESTED] no E2EE keyAgreement in Phase 1
  ├── [★★★ TESTED] invalid DID JSON / missing id
  ├── [★★★ TESTED] invalid PEM / missing auth / mismatched key
  └── [★★★ TESTED] atomic private key mode 0o600

[+] clients/anp-client/scripts/did_server.py                    [+] Local DID serving
  ├── [★★★ TESTED] DID route generation                          ├── [★★★ TESTED] serve-did loopback check
  ├── [★★★ TESTED] loopback vs non-loopback host                 └── [★★★ TESTED] IPv6 URL host formatting
  └── [★★★ TESTED] local-only output guidance

[+] clients/anp-client/scripts/anp_client.py discovery           [+] Public discovery
  ├── [★★★ TESTED] endpoint URL safety                           ├── [★★★ TESTED] discover --endpoint --json is read-only
  ├── [★★★ TESTED] AD URL safety                                 ├── [★★★ TESTED] discover --ad-url derives endpoints
  ├── [★★★ TESTED] redirect rejection                            └── [★★★ TESTED] missing chat still discoverable
  ├── [★★★ TESTED] non-ANP AD rejection
  ├── [★★★ TESTED] OpenRPC interface selection
  ├── [★★★ TESTED] OpenRPC servers[].url RPC endpoint
  └── [★★★ TESTED] require_chat gate for chat calls

[+] clients/anp-client/scripts/anp_client.py chat                [+] Signed chat
  ├── [★★★ TESTED] legacy params.message body                    ├── [★★★ TESTED] mock service captures Signature headers
  ├── [★★★ TESTED] DID WBA signature headers                     ├── [★★★ TESTED] chat --json parses response
  ├── [★★★ TESTED] JSON-RPC success                              └── [→E2E] real Hermes gateway discover + chat
  ├── [★★★ TESTED] JSON-RPC -32001/-32002/-32003 guidance
  ├── [★★★ TESTED] HTTP/network failure
  └── [★★★ TESTED] redirect rejection

[+] docs/package boundary                                       [+] Install bundle verification
  ├── [★★★ TESTED] required root files                           ├── [★★★ TESTED] no did.json/private_key.pem
  ├── [★★★ TESTED] no symlinks                                   └── [★★★ TESTED] no repo absolute path dependency
  └── [★★★ TESTED] requirements-dev verification entry

COVERAGE: 100% of planned Phase 1 paths mapped to tests.
QUALITY: ★★★ across security, identity, discovery, chat, E2E, and package-boundary paths.
```

### Failure Modes

- Identity partial write or mismatched key → covered by identity tests; user sees `IdentityError`, not a silent DID reset.
- Private key permissions drift → covered by `0o600` tests and atomic write helpers; no private key content is printed.
- `discover` accidentally creates caller identity → covered by CLI JSON integration test; user gets read-only discovery behavior.
- Non-loopback HTTP or redirect bypass → covered by URL and redirect tests; user sees a clear `ClientError`.
- Service lacks `chat` → `discover` still succeeds; `chat` fails with a method-list error.
- DID document cannot be resolved by service agent → JSON-RPC `-32002` maps to `serve-did` / `ANP_DID_RESOLVER_BASE_URL` guidance.
- Async CLI integration tests block their aiohttp server → fixed by async subprocess helpers with timeout.
- Remote HTTPS service cannot resolve default localhost DID → documented as out of Phase 1 and tracked as TODO-5.
- Critical silent gaps flagged: 0.

### Worktree Parallelization Strategy

| Step | Modules touched | Depends on |
|------|----------------|------------|
| Identity lane | `clients/anp-client/scripts/`, `clients/anp-client/tests/` | Task 1 skeleton |
| DID server + CLI basics | `clients/anp-client/scripts/`, `clients/anp-client/tests/` | Identity lane |
| Discovery lane | `clients/anp-client/scripts/`, `clients/anp-client/tests/` | DID server + CLI basics |
| Chat/signing lane | `clients/anp-client/scripts/`, `clients/anp-client/tests/` | Discovery lane |
| Docs/natural language lane | `clients/anp-client/`, `clients/anp-client/tests/` | CLI argument contract |
| E2E/quality lane | `plugins/anp-agent/tests/e2e/`, `clients/anp-client/tests/` | Discovery + chat/signing |

Recommended execution order:

- Sequential core: Task 1 → Task 2 → Task 3 → Task 4 → Task 5.
- Parallel after Task 5 is stable:
  - Lane A: Task 6 docs + natural-language examples.
  - Lane B: Task 7 E2E + integration hardening.
- Final sequential: Task 8 quality gate and OpenSpec verification.

Conflict flags:

- Tasks 2-5 all touch `clients/anp-client/scripts/anp_client.py` or adjacent script modules; do not parallelize those core implementation tasks without careful merge coordination.
- Task 6 and Task 7 can run in separate worktrees after the CLI contract stabilizes.

### Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific finding above. Run with Claude Code or Codex; checkbox as you ship.

- [ ] **T1 (P1, human: ~4h / CC: ~35min)** — identity — Implement robust DID identity validation and atomic writes.
  - Surfaced by: Architecture / Outside Voice — damaged or mismatched identity files must fail clearly; private key creation must be atomic and `0o600`; Phase 1 DID must not declare E2EE `keyAgreement`.
  - Files: `clients/anp-client/scripts/did_identity.py`, `clients/anp-client/tests/test_identity.py`, `clients/anp-client/requirements.txt`.
  - Verify: `python3 -m pytest clients/anp-client/tests/test_identity.py -q`.

- [ ] **T2 (P1, human: ~3h / CC: ~30min)** — discovery — Implement safe, read-only, OpenRPC-aware discovery.
  - Surfaced by: Architecture / Code Quality / Outside Voice — `discover` must be read-only, reject redirect bypass, separate discover/chat method validation, select OpenRPC interface, and honor `servers[].url`.
  - Files: `clients/anp-client/scripts/anp_client.py`, `clients/anp-client/tests/test_discovery.py`.
  - Verify: `python3 -m pytest clients/anp-client/tests/test_discovery.py -q`.

- [ ] **T3 (P1, human: ~3h / CC: ~25min)** — tests — Make integration/E2E tests reliable and complete.
  - Surfaced by: Test Review / Outside Voice — use local `aiohttp_unused_port`, async subprocess helpers with timeout, correct `ClientError` imports, and cover HTTP/JSON-RPC/package-boundary errors.
  - Files: `clients/anp-client/tests/conftest.py`, `clients/anp-client/tests/test_discovery.py`, `clients/anp-client/tests/test_chat.py`, `clients/anp-client/tests/test_package_boundary.py`, `plugins/anp-agent/tests/e2e/test_anp_client_skill.py`.
  - Verify: `python3 -m pytest clients/anp-client/tests -q` and `cd plugins/anp-agent && python3 -m pytest tests/e2e/test_echo.py tests/e2e/test_anp_client_skill.py -v --run-e2e`.

- [ ] **T4 (P2, human: ~2h / CC: ~20min)** — distribution — Define runtime and dev dependency boundaries for the client skill.
  - Surfaced by: Architecture / Outside Voice — package must be source-agnostic and self-contained, with reproducible local verification via `requirements-dev.txt`.
  - Files: `clients/anp-client/README.md`, `clients/anp-client/requirements-dev.txt`, `clients/anp-client/tests/test_package_boundary.py`.
  - Verify: `python3 -m pip install -r clients/anp-client/requirements-dev.txt` and Task 8 package boundary checks.

- [ ] **T5 (P2, human: ~1.5h / CC: ~15min)** — docs — Document Phase 1 localhost DID boundary and defer remote DID hosting.
  - Surfaced by: Outside Voice / TODO Review — default `did:wba:localhost...` supports same-machine loopback signed chat; remote HTTPS service support needs public DID hosting or hostname initialization.
  - Files: `clients/anp-client/SKILL.md`, `clients/anp-client/README.md`, `TODOS.md`, `openspec/changes/add-anp-client-skill/specs/anp-client-skill/spec.md`.
  - Verify: `openspec validate add-anp-client-skill --type change`.

### Completion Summary

- Step 0: Scope Challenge — scope accepted as-is after explicit user decision.
- Architecture Review: 2 issues found and applied (`discover` read-only; generic install bundle boundary).
- Code Quality Review: 2 issues found and applied (`client_home` shadowing; split discover/chat validation).
- Test Review: diagram produced, 2 initial gaps identified and applied (`aiohttp_unused_port`; ad-url/error/package-boundary coverage).
- Performance Review: 0 issues found.
- Outside voice: ran via Claude subagent; 10 findings evaluated and applied or explicitly scoped.
- NOT in scope: written.
- What already exists: written.
- TODOS.md updates: 1 item proposed and added (`TODO-5`).
- Failure modes: 0 critical silent gaps flagged.
- Parallelization: 6 lanes identified; core tasks mostly sequential, docs/E2E can parallelize after CLI contract stabilizes.
- Lake Score: 14/14 recommendations chose complete option.
- Unresolved decisions: 0.
