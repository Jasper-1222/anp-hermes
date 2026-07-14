# Simplify ANP Local Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 ANP client skill 与 Hermes ANP plugin 的本地安装包验证体验，让用户在 Hermes 安装 plugin、OpenClaw 安装 skill 后能用最少步骤完成本地对话测试。

**Architecture:** 保留生产安全边界，只在 loopback 本地场景降低摩擦。client 端增加 loopback endpoint 等价匹配与更明确的本地测试错误提示；文档与 manifest 面向安装包验证路径补充“本地测试推荐配置”；重新打包并验证 zip 不含运行态身份、缓存或绝对路径。

**Tech Stack:** Python 3.10+、aiohttp、ANP Python SDK、pytest、ruff、black、Hermes plugin manifest YAML、OpenClaw/Hermes skill zip 安装包。

## Global Constraints

- 官方语言为中文：文档、注释、业务语义命名、提交信息、Issue/PR 描述均使用中文。
- 所有操作必须在 WSL2 中执行，禁止调用 Windows 路径。
- 不降低非 loopback HTTP 的安全边界：仍拒绝公网/局域网明文 HTTP endpoint。
- 不自动修改 Hermes 用户配置文件，不自动批准配对码，不偷偷设置 home channel。
- 本地测试路径可以降低摩擦：loopback HTTP 的 `localhost`、`127.0.0.1`、`::1` 在同 scheme、同端口、同 path 时视为等价。
- `ANP_DID_RESOLVER_BASE_URL` 仍只允许 loopback base URL；它是 Hermes gateway 启动前环境变量。
- `ANP_ALLOW_ALL_USERS=1` 仅作为本地测试推荐配置；公开部署不要依赖该开关。
- 重新打包 zip 时不得包含 `did.json`、`private_key.pem`、`jwt_private_key.pem`、`jwt_public_key.pem`、`__pycache__`、`.pytest_cache`、`.ruff_cache`、`.venv`、egg-info 或本机绝对路径。
- Commit steps are optional: only commit if current execution session has explicit commit authorization.

---

## File Structure

### Modify

- `clients/anp-client/scripts/anp_client.py`
  - 新增 loopback endpoint 等价判断 helper。
  - 改善 discovery endpoint mismatch 错误。
  - 改善 JSON-RPC `-32002`、pairing code、home channel / `/sethome` 相关提示。

- `clients/anp-client/tests/test_discovery.py`
  - 覆盖 `localhost` 与 `127.0.0.1` 等价 endpoint。
  - 覆盖 path / port 不一致仍拒绝。

- `clients/anp-client/tests/test_chat.py`
  - 覆盖 `-32002` 本地测试引导包含 Hermes gateway 启动前 env 与重启说明。
  - 覆盖 pairing code / `/sethome` 文案提示映射。

- `clients/anp-client/SKILL.md`
  - 增加 OpenClaw 对话态安装后本地测试入口与故障处理说明。

- `clients/anp-client/README.md`
  - 增加“安装包态本地验证最短路径”。

- `plugins/anp-agent/plugin.yaml`
  - 调整 `ANP_ALLOW_ALL_USERS` prompt/description，使本地测试用户明确填写 `true`。
  - 增加 `ANP_DID_RESOLVER_BASE_URL` optional env 说明，强调本地测试值 `http://127.0.0.1:18900` 且需重启 gateway。

- `plugins/anp-agent/README.md`
  - 增加 Hermes 安装 plugin zip 后的本地测试推荐配置说明。

### Generated

- `dist/anp-agent-plugin-0.1.0.zip`
- `dist/anp-client-skill-0.1.0.zip`

---

### Task 1: Loopback Endpoint Equivalence

**Files:**
- Modify: `clients/anp-client/scripts/anp_client.py`
- Modify: `clients/anp-client/tests/test_discovery.py`

**Interfaces:**
- Consumes: existing `canonicalize_allowed_url(url: str) -> str`, `normalize_endpoint(endpoint: str) -> str`.
- Produces:
  - `loopback_endpoints_equivalent(left: str, right: str) -> bool`
  - discovery accepts loopback host aliases when scheme, port, and path are equivalent.

- [ ] **Step 1: Add failing tests for loopback endpoint aliases**

Append to `clients/anp-client/tests/test_discovery.py`:

```python
@pytest.mark.asyncio
async def test_discover_service_accepts_loopback_endpoint_alias() -> None:
    requested_endpoint = "http://127.0.0.1:8900"
    ad_endpoint = "http://localhost:8900"

    async def ad_handler(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "protocolType": "ANP",
                "name": "Loopback Alias 服务",
                "did": "did:wba:localhost:agent:e1_loopback_alias",
                "endpoint": ad_endpoint,
                "interfaces": [
                    {"type": "openrpc", "url": f"{ad_endpoint}/agent/interface.json"}
                ],
            }
        )

    async def interface_handler(request: web.Request) -> web.Response:
        return web.json_response({"openrpc": "1.3.2", "methods": [{"name": "chat"}]})

    app = web.Application()
    app.router.add_get("/agent/ad.json", ad_handler)
    app.router.add_get("/agent/interface.json", interface_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8900)
    await site.start()
    try:
        service = await discover_service(endpoint=requested_endpoint, ad_url=None)
    finally:
        await runner.cleanup()

    assert service.service_did == "did:wba:localhost:agent:e1_loopback_alias"
    assert service.rpc_endpoint == "http://localhost:8900/agent/rpc"
```

Add direct helper tests:

```python
@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("http://127.0.0.1:8900", "http://localhost:8900"),
        ("http://localhost:8900", "http://127.0.0.1:8900"),
        ("http://[::1]:8900", "http://localhost:8900"),
        ("http://127.0.0.1:8900/anp", "http://localhost:8900/anp"),
    ],
)
def test_loopback_endpoints_equivalent_accepts_aliases(left: str, right: str) -> None:
    assert anp_client.loopback_endpoints_equivalent(left, right)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("http://127.0.0.1:8900", "http://localhost:8901"),
        ("http://127.0.0.1:8900/anp", "http://localhost:8900"),
        ("https://example.com", "https://other.example.com"),
        ("http://127.0.0.1:8900", "https://localhost:8900"),
    ],
)
def test_loopback_endpoints_equivalent_rejects_real_mismatch(left: str, right: str) -> None:
    assert not anp_client.loopback_endpoints_equivalent(left, right)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_discovery.py -q
```

Expected: FAIL because `loopback_endpoints_equivalent` does not exist and discovery still rejects `localhost` / `127.0.0.1` mismatch.

- [ ] **Step 3: Implement endpoint equivalence helper**

In `clients/anp-client/scripts/anp_client.py`, add after `normalize_endpoint()`:

```python
def _loopback_host(host: str | None) -> bool:
    """判断 URL hostname 是否为 loopback。"""
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def loopback_endpoints_equivalent(left: str, right: str) -> bool:
    """判断两个 endpoint 是否为本地 loopback 等价地址。"""
    try:
        left_parsed = urlparse(left)
        right_parsed = urlparse(right)
        left_port = left_parsed.port
        right_port = right_parsed.port
    except ValueError:
        return False

    if left_parsed.scheme != right_parsed.scheme:
        return False
    if left_parsed.scheme != "http":
        return False
    if left_port != right_port:
        return False
    if (left_parsed.path.rstrip("/") or "") != (right_parsed.path.rstrip("/") or ""):
        return False
    if left_parsed.params or right_parsed.params:
        return False
    if left_parsed.query or right_parsed.query:
        return False
    return _loopback_host(left_parsed.hostname) and _loopback_host(right_parsed.hostname)
```

- [ ] **Step 4: Use helper in discovery mismatch check**

Replace this block in `discover_service()`:

```python
        if normalized_endpoint and normalized_endpoint != ad_endpoint:
            raise ClientError("Agent Description RPC endpoint 与请求 endpoint 不一致")
```

with:

```python
        if normalized_endpoint and normalized_endpoint != ad_endpoint:
            if not loopback_endpoints_equivalent(normalized_endpoint, ad_endpoint):
                raise ClientError(
                    "Agent Description RPC endpoint 与请求 endpoint 不一致；"
                    "本地测试请优先使用服务端 ad.json 中声明的 endpoint，"
                    "或确保 localhost / 127.0.0.1 使用相同端口和路径。"
                )
```

- [ ] **Step 5: Run discovery tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_discovery.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit if authorized**

```bash
git add clients/anp-client/scripts/anp_client.py clients/anp-client/tests/test_discovery.py
git commit -m "fix: 放宽本地 ANP endpoint 等价匹配"
```

---

### Task 2: Local-Test Guidance in Client Errors

**Files:**
- Modify: `clients/anp-client/scripts/anp_client.py`
- Modify: `clients/anp-client/tests/test_chat.py`

**Interfaces:**
- Consumes: existing `format_rpc_error(error: dict[str, Any]) -> str`.
- Produces:
  - `format_rpc_error()` messages that guide OpenClaw/Hermes local package validation.
  - pairing and `/sethome` hints when service reply text contains those known Hermes prompts.

- [ ] **Step 1: Add failing tests for clearer local guidance**

In `clients/anp-client/tests/test_chat.py`, update the existing `test_format_rpc_error_guidance` expected strings for `-32002` to include `Hermes gateway 启动前`.

Add:

```python
def test_format_rpc_error_did_resolver_guidance_names_hermes_gateway() -> None:
    message = format_rpc_error({"code": -32002, "message": "DID 文档无法解析"})

    assert "Hermes gateway 启动前" in message
    assert "ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900" in message
    assert "ANP_ALLOW_ALL_USERS=1" in message
    assert "重启 Hermes gateway" in message
```

Add tests for known Hermes response hints:

```python
def test_local_response_guidance_detects_pairing_code() -> None:
    text = "Hi~ I don't recognize you yet! Pairing code: G8T97879"

    guidance = anp_client.local_response_guidance(text)

    assert "ANP_ALLOW_ALL_USERS=1" in guidance
    assert "hermes pairing approve anp G8T97879" in guidance


def test_local_response_guidance_detects_sethome_prompt() -> None:
    text = "No home channel is set for Anp. Type /sethome to make this chat your home channel."

    guidance = anp_client.local_response_guidance(text)

    assert "发送 /sethome" in guidance
    assert "只需执行一次" in guidance
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

Expected: FAIL because `local_response_guidance` does not exist and `-32002` guidance is too vague.

- [ ] **Step 3: Implement local response guidance helper**

In `clients/anp-client/scripts/anp_client.py`, add after `format_rpc_error()`:

```python
def local_response_guidance(text: str) -> str:
    """根据 Hermes 常见本地测试回复生成下一步提示。"""
    lines: list[str] = []
    pairing_match = re.search(r"Pairing code:\s*([A-Z0-9]+)", text)
    if pairing_match:
        code = pairing_match.group(1)
        lines.append(
            "本地测试建议在 Hermes gateway 启动前设置 ANP_ALLOW_ALL_USERS=1 后重启，"
            "避免每个临时 DID 都触发配对。"
        )
        lines.append(f"如果要保留配对流程，可运行: hermes pairing approve anp {code}")
    if "No home channel" in text or "/sethome" in text or "home channel" in text:
        lines.append("如 Hermes 提示未设置 home channel，请通过 ANP 发送 /sethome；本地验证通常只需执行一次。")
    return "\n".join(lines)
```

- [ ] **Step 4: Improve `-32002` guidance**

Replace `format_rpc_error()` branch for `code == -32002` with:

```python
    if code == -32002:
        lines.append("本地测试下，服务端 Hermes gateway 无法解析个人智能体 DID 文档。")
        lines.append("请确认 OpenClaw/anp-client 已启动 serve-did，默认地址为 http://127.0.0.1:18900。")
        lines.append("请在 Hermes gateway 启动前设置：")
        lines.append("  ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900")
        lines.append("  ANP_ALLOW_ALL_USERS=1")
        lines.append("设置后需要重启 Hermes gateway；运行中修改环境变量不会生效。")
```

- [ ] **Step 5: Append guidance to human chat output**

In `_cmd_chat()`, replace:

```python
    print(result["response"])
    return 0
```

with:

```python
    print(result["response"])
    guidance = local_response_guidance(result["response"])
    if guidance:
        print("\n本地测试提示:")
        print(guidance)
    return 0
```

Do not append guidance to `--json` output; keep JSON stable.

- [ ] **Step 6: Run chat tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit if authorized**

```bash
git add clients/anp-client/scripts/anp_client.py clients/anp-client/tests/test_chat.py
git commit -m "fix: 改善 ANP client 本地测试错误提示"
```

---

### Task 3: Install-Package Documentation and Manifest Prompts

**Files:**
- Modify: `clients/anp-client/SKILL.md`
- Modify: `clients/anp-client/README.md`
- Modify: `plugins/anp-agent/plugin.yaml`
- Modify: `plugins/anp-agent/README.md`

**Interfaces:**
- Consumes: existing CLI commands `serve-did`, `discover`, `chat`.
- Produces: clear package-state validation instructions for Hermes plugin zip + OpenClaw skill zip.

- [ ] **Step 1: Update plugin manifest prompts**

In `plugins/anp-agent/plugin.yaml`, replace the `ANP_ALLOW_ALL_USERS` entry with:

```yaml
  - name: ANP_ALLOW_ALL_USERS
    description: "本地测试推荐 true，用于允许任意 DID WBA 调用方访问；公开部署请改为 false 并配置 ANP_ALLOWED_USERS。"
    prompt: "本地测试请输入 true；公开部署请输入 false"
    password: false
```

Add under `optional_env`:

```yaml
  - name: ANP_DID_RESOLVER_BASE_URL
    description: "本地测试 DID 文档服务地址；OpenClaw/anp-client serve-did 默认值为 http://127.0.0.1:18900，需在 Hermes gateway 启动前设置。"
    prompt: "本地 DID resolver base URL"
    password: false
```

- [ ] **Step 2: Update skill docs for OpenClaw dialogue validation**

Append to `clients/anp-client/SKILL.md`:

```markdown
## OpenClaw 本地安装包验证

推荐用户先在 Hermes 安装 `anp-agent` plugin zip，并在本地测试时让 Hermes gateway 启动前具备：

```bash
ANP_ALLOW_ALL_USERS=1
ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

在 OpenClaw 安装本 skill 后，若用户说：

```text
通过 ANP 调用 http://localhost:8900 的服务智能体，问它“请介绍下自己”
```

执行等价流程：

```bash
python3 scripts/anp_client.py chat --endpoint http://localhost:8900 --message "请介绍下自己"
```

如服务回复 pairing code，提示用户本地测试应确认 Hermes gateway 启动前设置 `ANP_ALLOW_ALL_USERS=1` 并重启；若保留配对流程，则运行 `hermes pairing approve anp <code>`。

如服务提示 home channel，提示用户通过 ANP 发送 `/sethome` 一次。
```

- [ ] **Step 3: Update client README with shortest package validation path**

Add near the top of `clients/anp-client/README.md` after install dependencies:

```markdown
## 安装包态本地验证最短路径

1. 在 Hermes 中安装 `anp-agent` plugin zip。
2. 本地测试时，Hermes gateway 启动前设置：

```bash
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

3. 在 OpenClaw 中安装 `anp-client` skill zip。
4. 在 OpenClaw 对话中启动本地 DID 文档服务，默认监听 `127.0.0.1:18900`。
5. 对 OpenClaw 说：

```text
通过 ANP 调用 http://localhost:8900 的服务智能体，问它“请介绍下自己”
```

如果 Hermes 已经在运行后才设置环境变量，需要重启 Hermes gateway。`localhost` 与 `127.0.0.1` 在本地同端口场景会被视为等价。
```

- [ ] **Step 4: Update plugin README**

Add to `plugins/anp-agent/README.md` a section:

```markdown
## 本地安装包验证推荐配置

通过 Hermes 对话框安装 plugin zip 后，本地测试建议在 Hermes gateway 启动前设置：

```bash
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

`ANP_ALLOW_ALL_USERS=1` 只建议用于本地验证，可避免 OpenClaw/anp-client 每次生成临时 DID 后触发配对授权。公开部署请关闭该开关，并使用 `ANP_ALLOWED_USERS` 配置允许的调用方 DID。

`ANP_DID_RESOLVER_BASE_URL` 让服务端在本地测试时通过 OpenClaw/anp-client 的 `serve-did` 解析调用方 DID 文档。该变量在 ANP 认证器初始化时读取，因此运行中的 Hermes gateway 修改环境变量不会生效，需要重启 gateway。
```

- [ ] **Step 5: Run docs/package tests**

Run:

```bash
python3 -m pytest clients/anp-client/tests/test_package_boundary.py clients/anp-client/tests/test_natural_language_examples.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit if authorized**

```bash
git add clients/anp-client/SKILL.md clients/anp-client/README.md plugins/anp-agent/plugin.yaml plugins/anp-agent/README.md
git commit -m "docs: 补充 ANP 本地安装包验证引导"
```

---

### Task 4: Verification and Repackage

**Files:**
- Modify generated package files under `dist/`.
- Test: client tests, focused plugin tests, package boundary checks.

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces:
  - `dist/anp-agent-plugin-0.1.0.zip`
  - `dist/anp-client-skill-0.1.0.zip`

- [ ] **Step 1: Run client regression suite**

Run:

```bash
python3 -m pytest clients/anp-client/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run formatting and lint**

Run:

```bash
black --check clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
ruff check clients/anp-client/scripts clients/anp-client/tests plugins/anp-agent/tests/e2e/test_anp_client_skill.py
```

Expected: both PASS.

- [ ] **Step 3: Run focused plugin tests**

Run:

```bash
cd plugins/anp-agent && python3 -m pytest tests/test_integration.py tests/test_server.py -q
```

Expected: PASS.

- [ ] **Step 4: Run OpenSpec validation**

Run:

```bash
openspec validate --all
```

Expected: all specs passed.

- [ ] **Step 5: Rebuild sanitized package directories and zip files**

Run from repo root:

```bash
rm -rf dist/anp-agent-plugin dist/anp-client-skill
mkdir -p dist/anp-agent-plugin dist/anp-client-skill
cp plugins/anp-agent/plugin.yaml plugins/anp-agent/__init__.py plugins/anp-agent/README.md plugins/anp-agent/pyproject.toml dist/anp-agent-plugin/
cp -R plugins/anp-agent/anp_agent dist/anp-agent-plugin/anp_agent
cp clients/anp-client/SKILL.md clients/anp-client/README.md clients/anp-client/requirements.txt dist/anp-client-skill/
cp -R clients/anp-client/scripts dist/anp-client-skill/scripts
find dist/anp-agent-plugin dist/anp-client-skill -type d -name __pycache__ -prune -exec rm -rf {} +
find dist/anp-agent-plugin dist/anp-client-skill -type d \( -name .pytest_cache -o -name .ruff_cache -o -name .venv -o -name '*.egg-info' \) -prune -exec rm -rf {} +
find dist/anp-agent-plugin dist/anp-client-skill -type f \( -name '*.pyc' -o -name 'did.json' -o -name 'private_key.pem' -o -name 'jwt_private_key.pem' -o -name 'jwt_public_key.pem' -o -name '*.tmp' -o -name '*.bak*' -o -name '.coverage' \) -delete
python3 - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

for src_name, zip_name in [
    ("dist/anp-agent-plugin", "dist/anp-agent-plugin-0.1.0.zip"),
    ("dist/anp-client-skill", "dist/anp-client-skill-0.1.0.zip"),
]:
    src = Path(src_name)
    out = Path(zip_name)
    if out.exists():
        out.unlink()
    with ZipFile(out, "w", ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())
    print(out)
PY
```

Expected: both zip paths printed.

- [ ] **Step 6: Verify package boundaries**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile

for name in ["dist/anp-agent-plugin-0.1.0.zip", "dist/anp-client-skill-0.1.0.zip"]:
    with ZipFile(name) as zf:
        names = zf.namelist()
        forbidden = [
            n for n in names
            if n.endswith(".pyc")
            or "__pycache__" in n
            or n in {"did.json", "private_key.pem", "jwt_private_key.pem", "jwt_public_key.pem"}
            or n.endswith(".tmp")
            or ".pytest_cache" in n
            or ".ruff_cache" in n
            or ".venv" in n
            or ".egg-info/" in n
        ]
        absolute_hits = []
        for n in names:
            if n.endswith((".py", ".md", ".txt", ".yaml", ".toml")):
                data = zf.read(n).decode("utf-8")
                if "/home/peter/anp-hermes" in data:
                    absolute_hits.append(n)
        print(f"{name}: files={len(names)} forbidden={forbidden} absolute_hits={absolute_hits}")
        if forbidden or absolute_hits:
            raise SystemExit(1)
for path in ["dist/anp-agent-plugin-0.1.0.zip", "dist/anp-client-skill-0.1.0.zip"]:
    p = Path(path)
    print(f"{path} {p.stat().st_size} bytes")
PY
```

Expected: `forbidden=[] absolute_hits=[]` for both zip files.

- [ ] **Step 7: Commit if authorized**

```bash
git add dist/anp-agent-plugin-0.1.0.zip dist/anp-client-skill-0.1.0.zip
git commit -m "build: 更新 ANP 本地验证安装包"
```

If zip artifacts are intentionally not tracked, skip commit and report the paths.

---

## Self-Review

### Spec Coverage

- Loopback endpoint mismatch: Task 1 adds helper and tests for `localhost` / `127.0.0.1` / `::1` equivalence while keeping real mismatches rejected.
- DID resolver local guidance: Task 2 expands `-32002` message with `ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900`, `ANP_ALLOW_ALL_USERS=1`, and restart requirement.
- Pairing and `/sethome` friction: Task 2 detects known Hermes response text and prints next-step guidance for non-JSON chat output.
- Plugin install prompts: Task 3 updates `plugin.yaml` prompt text and optional resolver env description.
- OpenClaw skill install guidance: Task 3 updates `SKILL.md` and client README with dialogue-first local validation path.
- Zip package validation: Task 4 rebuilds sanitized plugin and skill packages and verifies boundaries.

### Placeholder Scan

No `TBD`, `TODO`, unspecified validation, or open-ended “add tests” steps remain. Each task includes exact files, code snippets, commands, and expected outcomes.

### Type Consistency

- `loopback_endpoints_equivalent(left: str, right: str) -> bool` is defined in Task 1 and referenced only from discovery and tests.
- `local_response_guidance(text: str) -> str` is defined in Task 2 and used only for non-JSON chat output.
- `format_rpc_error(error: dict[str, Any]) -> str` keeps its existing signature.

## Execution Handoff

Plan complete. Use either subagent-driven or inline execution after user chooses execution mode. Do not start implementation until execution mode is selected.
