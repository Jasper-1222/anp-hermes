# 重构 ANP 认证错误分类 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `anp-agent` 插件的 DID WBA 认证失败响应从统一的“认证失败”重构为 6 个结构化 JSON-RPC 错误码，提升调用方可观测性。

**Architecture:** 在 `auth.py` 中扩展 `AuthenticationError` 并新增 `_classify_verifier_error` 分类器，使所有认证失败携带 `status_code`、`rpc_code`、`headers`；`server.py` 的 `_map_auth_error` 直接读取这些元数据构造响应，不再反向解析异常字符串。

**Tech Stack:** Python 3.12, aiohttp, ANP Python SDK (`anp.authentication`), pytest, ruff, black.

## Global Constraints

- 使用 ANP 原生 DID WBA 身份（`did:wba:`），不使用 `did:cn` 或其他 DID 方法。
- 不依赖 DTR、Portal、Mediator、OpenClaw 等外部基础设施，仅使用 ANP Python SDK 和 Hermes 插件机制。
- 插件必须零侵入 Hermes 核心代码。
- 本次变更仅涉及身份认证错误分类 + JSON-RPC 调用响应，不触碰 AP2 支付与 E2EE 加密。
- 所有文档、代码注释、业务语义命名、提交信息使用中文。
- 测试覆盖率要求 ≥ 85%。
- 代码需通过 `ruff check .` 与 `black --check .`。

## OpenSpec Context

本计划基于 OpenSpec 变更 `refactor-anp-auth-error-handling`：
- `openspec/changes/refactor-anp-auth-error-handling/proposal.md`
- `openspec/changes/refactor-anp-auth-error-handling/design.md`
- `openspec/changes/refactor-anp-auth-error-handling/specs/anp-auth-error-classification/spec.md`
- `openspec/changes/refactor-anp-auth-error-handling/specs/anp-platform-adapter/spec.md`

## File Structure

| 文件 | 职责 |
|---|---|
| `plugins/anp-agent/auth.py` | 扩展 `AuthenticationError`、新增错误分类器、修复 resolver wrapper、更新 `authenticate` 异常路径。 |
| `plugins/anp-agent/server.py` | 新增错误码常量、重写 `_map_auth_error`、转发 challenge 头。 |
| `plugins/anp-agent/tests/test_auth.py` | 断言 `AuthenticationError` 字段与分类器行为，新增网络/内部错误场景。 |
| `plugins/anp-agent/tests/test_server.py` | 断言各错误码的 HTTP/JSON-RPC 映射与 challenge 头转发。 |
| `plugins/anp-agent/tests/test_integration.py` | 更新集成测试中缺少签名场景的断言为 `-32003`。 |

## 错误码契约

| rpc_code | HTTP status | 对外消息 | 触发场景 |
|---|---|---|---|
| `-32001` | 401 | DID WBA 签名无效 | 签名验证失败、时间戳/nonce/keyid 无效 |
| `-32002` | 401 | DID 文档无法解析 | DID 文档解析超时、网络错误、HTTPS 解析失败 |
| `-32003` | 401 | 缺少认证头 | 缺少 Signature / Signature-Input / Authorization |
| `-32004` | 401 | DID 文档无效 | DID 文档 proof / binding / 结构校验失败 |
| `-32005` | 403 | 认证方法未授权 | verification method 未列入 authentication |
| `-32006` | 500 | 认证服务内部错误 | 认证过程中未预期内部异常 |

---

### Task 1: 扩展 AuthenticationError 结构

**Files:**
- Modify: `plugins/anp-agent/auth.py:44-46`
- Test: `plugins/anp-agent/tests/test_auth.py`

**Interfaces:**
- Consumes: 无
- Produces: `AuthenticationError(message, *, status_code=401, rpc_code=-32001, headers=None)`，字段保持向后兼容（旧式 `AuthenticationError("认证失败")` 仍可工作）。

- [ ] **Step 1.1: 编写失败测试**

在 `plugins/anp-agent/tests/test_auth.py` 末尾新增：

```python
@pytest.mark.asyncio
async def test_authentication_error_carries_structured_fields() -> None:
    """AuthenticationError 应携带结构化字段。"""
    exc = AuthenticationError(
        "缺少认证头",
        status_code=401,
        rpc_code=-32003,
        headers={"WWW-Authenticate": "test"},
    )
    assert str(exc) == "缺少认证头"
    assert exc.status_code == 401
    assert exc.rpc_code == -32003
    assert exc.headers == {"WWW-Authenticate": "test"}
```

- [ ] **Step 1.2: 运行测试确认失败**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_authentication_error_carries_structured_fields -v
```

Expected: FAIL（`AuthenticationError` 不接受关键字参数）。

- [ ] **Step 1.3: 实现扩展**

替换 `plugins/anp-agent/auth.py:44-46`：

```python
class AuthenticationError(Exception):
    """认证失败时抛出的结构化异常。

    携带 HTTP 状态码、JSON-RPC 错误码与可选 challenge 头，
    供 server.py 直接构造对外响应，无需反向解析原始异常。
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 401,
        rpc_code: int = -32001,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.rpc_code = rpc_code
        self.headers = headers
```

- [ ] **Step 1.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_authentication_error_carries_structured_fields -v
```

Expected: PASS。

- [ ] **Step 1.5: 提交**

```bash
git add plugins/anp-agent/auth.py plugins/anp-agent/tests/test_auth.py
git commit -m "feat(auth): 扩展 AuthenticationError 携带 status_code、rpc_code、headers"
```

---

### Task 2: 新增 verifier 错误分类器

**Files:**
- Modify: `plugins/anp-agent/auth.py`（在 `_make_resolver_wrapper` 前新增 `_classify_verifier_error`）
- Test: `plugins/anp-agent/tests/test_auth.py`

**Interfaces:**
- Consumes: `DidWbaVerifierError`（含 `message`, `status_code`, `headers`）
- Produces: `_classify_verifier_error(exc) -> tuple[str, int, int]` 返回 `(对外消息, HTTP status, rpc_code)`。

- [ ] **Step 2.1: 编写失败测试**

在 `plugins/anp-agent/tests/test_auth.py` 中新增导入并添加测试：

```python
from anp.authentication.did_wba_verifier import DidWbaVerifierError
```

新增测试：

```python
@pytest.mark.parametrize(
    "message,status_code,expected_code",
    [
        ("Failed to resolve DID document: timeout", 401, -32002),
        ("Missing Signature-Input header", 401, -32003),
        ("Missing Signature header", 401, -32003),
        ("Invalid DID document proof", 401, -32004),
        ("Verification method not in authentication", 401, -32005),
        ("Signature verification failed", 401, -32001),
        ("Nonce verification failed", 401, -32001),
    ],
)
def test_classify_verifier_error_maps_known_errors(message, status_code, expected_code) -> None:
    """已知 verifier 错误应映射到正确错误码。"""
    from auth import _classify_verifier_error

    exc = DidWbaVerifierError(message, status_code=status_code)
    _, _, rpc_code = _classify_verifier_error(exc)
    assert rpc_code == expected_code
```

- [ ] **Step 2.2: 运行测试确认失败**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_classify_verifier_error_maps_known_errors -v
```

Expected: FAIL（`_classify_verifier_error` 未定义）。

- [ ] **Step 2.3: 实现分类器**

在 `plugins/anp-agent/auth.py` 中，`_resolver_config` 定义之后、`_make_resolver_wrapper` 之前插入：

```python
def _classify_verifier_error(exc: DidWbaVerifierError) -> tuple[str, int, int]:
    """根据 DidWbaVerifierError 消息与状态码分类认证失败。

    Returns:
        (对外消息, HTTP 状态码, JSON-RPC 错误码)
    """
    message = (exc.message or "").lower()

    # DID 文档解析失败：超时、网络错误、HTTPS 解析失败
    if "resolve did" in message or (
        "did document" in message and "timeout" in message
    ):
        return "DID 文档无法解析", 401, -32002

    # 缺少认证头
    if "missing" in message and any(
        keyword in message for keyword in ("signature", "authorization", "signature-input")
    ):
        return "缺少认证头", 401, -32003

    # DID 文档无效：proof / binding / 结构校验失败
    if any(
        keyword in message
        for keyword in ("invalid did document", "proof", "binding")
    ):
        return "DID 文档无效", 401, -32004

    # 认证方法未授权
    if "verification method" in message or "not in authentication" in message:
        return "认证方法未授权", 403, -32005

    # 默认：签名相关错误
    return "DID WBA 签名无效", 401, -32001
```

- [ ] **Step 2.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_classify_verifier_error_maps_known_errors -v
```

Expected: PASS。

- [ ] **Step 2.5: 提交**

```bash
git add plugins/anp-agent/auth.py plugins/anp-agent/tests/test_auth.py
git commit -m "feat(auth): 新增 DidWbaVerifierError 错误分类器"
```

---

### Task 3: 更新 ANPAuth.authenticate 使用分类器

**Files:**
- Modify: `plugins/anp-agent/auth.py:153-191`
- Test: `plugins/anp-agent/tests/test_auth.py`

**Interfaces:**
- Consumes: `_classify_verifier_error`, `AuthenticationError` 新构造方式
- Produces: `ANPAuth.authenticate` 抛出的 `AuthenticationError` 携带具体 `rpc_code`、`status_code`、`headers`。

- [ ] **Step 3.1: 编写失败测试**

在 `plugins/anp-agent/tests/test_auth.py` 中新增导入：

```python
from unittest.mock import AsyncMock
```

替换 `test_missing_signature_raises`：

```python
@pytest.mark.asyncio
async def test_missing_signature_raises(auth) -> None:
    """缺少认证头时应抛出 -32003。"""
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.authenticate(
            "POST",
            "http://localhost:8900/agent/rpc",
            {"Content-Type": "application/json"},
            "{}",
        )
    assert exc_info.value.rpc_code == -32003
    assert exc_info.value.status_code == 401
```

替换 `test_invalid_signature_raises`：

```python
@pytest.mark.asyncio
async def test_invalid_signature_raises(auth, caller_identity: dict) -> None:
    """签名无效时应抛出 -32001。"""
    target_url = "http://localhost:8900/agent/rpc"
    body = json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {}, "id": "1"})
    headers = await build_signed_headers(caller_identity, target_url, body)

    headers["Signature"] = "sig1=:invalid_signature:"

    with pytest.raises(AuthenticationError) as exc_info:
        await auth.authenticate("POST", target_url, headers, body)
    assert exc_info.value.rpc_code == -32001
```

新增内部错误测试：

```python
@pytest.mark.asyncio
async def test_unexpected_exception_returns_internal_auth_error(
    identity: ANPIdentity,
) -> None:
    """认证器内部未预期异常应映射为 -32006。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(side_effect=RuntimeError("模拟内部错误"))

    try:
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {"Content-Type": "application/json"},
                "{}",
            )
        assert exc_info.value.rpc_code == -32006
        assert exc_info.value.status_code == 500
    finally:
        auth._verifier.verify_request = original
```

- [ ] **Step 3.2: 运行测试确认失败**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_missing_signature_raises tests/test_auth.py::test_invalid_signature_raises tests/test_auth.py::test_unexpected_exception_returns_internal_auth_error -v
```

Expected: FAIL（`rpc_code` 断言失败，因为当前全部返回默认 -32001）。

- [ ] **Step 3.3: 实现 authenticate 更新**

确认 `plugins/anp-agent/auth.py` 顶部已导入 `aiohttp`：

```python
import aiohttp
```

替换 `plugins/anp-agent/auth.py:153-191` 的 `authenticate` 方法：

```python
    async def authenticate(
        self,
        method: str,
        url: str,
        headers: dict,
        body: str | bytes | None = None,
    ) -> str:
        """验证 HTTP 请求签名并返回调用方 DID。

        Args:
            method: HTTP 方法，如 "POST"。
            url: 请求完整 URL。
            headers: 请求头字典，需包含 Signature-Input / Signature。
            body: 请求体，可选。

        Returns:
            调用方 DID 字符串。

        Raises:
            AuthenticationError: 结构化认证失败异常，携带 status_code、rpc_code、headers。
        """
        try:
            result = await self._verifier.verify_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
            )
            caller_did = result.get("did")
            if not isinstance(caller_did, str):
                logger.error("DidWbaVerifier 返回结果缺少 did 字段: %s", result)
                raise AuthenticationError(
                    "DID WBA 签名无效",
                    status_code=401,
                    rpc_code=-32001,
                )
            return caller_did
        except DidWbaVerifierError as exc:
            logger.warning("DID WBA 认证失败: %s", exc)
            message, status_code, rpc_code = _classify_verifier_error(exc)
            raise AuthenticationError(
                message,
                status_code=status_code,
                rpc_code=rpc_code,
                headers=exc.headers,
            ) from exc
        except asyncio.TimeoutError as exc:
            logger.warning("DID 文档解析超时: %s", exc)
            raise AuthenticationError(
                "DID 文档无法解析",
                status_code=401,
                rpc_code=-32002,
            ) from exc
        except aiohttp.ClientError as exc:
            logger.warning("DID 文档解析网络错误: %s", exc)
            raise AuthenticationError(
                "DID 文档无法解析",
                status_code=401,
                rpc_code=-32002,
            ) from exc
        except Exception as exc:
            logger.exception("认证过程中发生未预期异常")
            raise AuthenticationError(
                "认证服务内部错误",
                status_code=500,
                rpc_code=-32006,
            ) from exc
```

- [ ] **Step 3.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_missing_signature_raises tests/test_auth.py::test_invalid_signature_raises tests/test_auth.py::test_unexpected_exception_returns_internal_auth_error -v
```

Expected: PASS。

- [ ] **Step 3.5: 提交**

```bash
git add plugins/anp-agent/auth.py plugins/anp-agent/tests/test_auth.py
git commit -m "feat(auth): authenticate 使用分类器并处理网络/内部异常"
```

---

### Task 4: 修复 resolver wrapper 对 aiohttp.ClientError 的包装

**Files:**
- Modify: `plugins/anp-agent/auth.py:52-80`
- Test: `plugins/anp-agent/tests/test_auth.py`

**Interfaces:**
- Consumes: `_resolver_config["base_url"]`, 原始 `resolve_did_wba_document`
- Produces: wrapper 将 `aiohttp.ClientError` 与 `asyncio.TimeoutError` 均包装为 `DidWbaVerifierError("Failed to resolve DID document: ...", status_code=401)`。

- [ ] **Step 4.1: 编写失败测试**

新增测试：

```python
@pytest.mark.asyncio
async def test_bad_resolver_base_url_returns_unresolvable_error(
    identity: ANPIdentity,
) -> None:
    """错误的 ANP_DID_RESOLVER_BASE_URL 应映射为 -32002。"""
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = "http://127.0.0.1:1"
    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32002
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
```

- [ ] **Step 4.2: 运行测试确认失败**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_bad_resolver_base_url_returns_unresolvable_error -v
```

Expected: FAIL（当前 `aiohttp.ClientError` 被外层 `except Exception` 捕获，返回 -32006 或 -32001）。

- [ ] **Step 4.3: 实现 wrapper 修复**

替换 `_make_resolver_wrapper` 中的异常处理部分：

```python
        try:
            if base_url is not None:
                coro = resolve_did_document(
                    did,
                    verify_proof=verify_proof,
                    base_url_override=base_url,
                    verify_ssl=False,
                )
            else:
                coro = resolve_fn(did, verify_proof=verify_proof)
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise DidWbaVerifierError(
                "Failed to resolve DID document: timeout",
                status_code=401,
            ) from exc
        except aiohttp.ClientError as exc:
            raise DidWbaVerifierError(
                f"Failed to resolve DID document: {exc.__class__.__name__}",
                status_code=401,
            ) from exc
```

- [ ] **Step 4.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py::test_bad_resolver_base_url_returns_unresolvable_error -v
```

Expected: PASS。

- [ ] **Step 4.5: 提交**

```bash
git add plugins/anp-agent/auth.py plugins/anp-agent/tests/test_auth.py
git commit -m "fix(auth): resolver wrapper 将 aiohttp.ClientError 包装为 DID 解析失败"
```

---

### Task 5: 更新 server.py 错误映射与 challenge 头转发

**Files:**
- Modify: `plugins/anp-agent/server.py:31-248`, `plugins/anp-agent/server.py:275-280`
- Test: `plugins/anp-agent/tests/test_server.py`

**Interfaces:**
- Consumes: `AuthenticationError` 的 `status_code`, `rpc_code`, `message`, `headers`
- Produces: `_map_auth_error(exc) -> tuple[ANPRPCError, dict[str, str] | None]`；HTTP 响应携带正确状态码与 challenge 头。

- [ ] **Step 5.1: 编写失败测试**

在 `plugins/anp-agent/tests/test_server.py` 中新增测试：

```python
@pytest.mark.asyncio
async def test_post_rpc_missing_auth_returns_401_and_minus_32003(
    client: TestClient,
    mock_auth: MagicMock,
):
    """缺少认证头返回 HTTP 401 与 JSON-RPC -32003。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "缺少认证头",
            status_code=401,
            rpc_code=-32003,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-missing-auth",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32003
    assert data["error"]["message"] == "缺少认证头"


@pytest.mark.asyncio
async def test_post_rpc_invalid_did_document_returns_401_and_minus_32004(
    client: TestClient,
    mock_auth: MagicMock,
):
    """DID 文档无效返回 HTTP 401 与 JSON-RPC -32004。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID 文档无效",
            status_code=401,
            rpc_code=-32004,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-invalid-did",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32004


@pytest.mark.asyncio
async def test_post_rpc_unauthorized_verification_method_returns_403_and_minus_32005(
    client: TestClient,
    mock_auth: MagicMock,
):
    """认证方法未授权返回 HTTP 403 与 JSON-RPC -32005。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "认证方法未授权",
            status_code=403,
            rpc_code=-32005,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-unauthorized-vm",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 403
    data = await resp.json()
    assert data["error"]["code"] == -32005


@pytest.mark.asyncio
async def test_post_rpc_internal_auth_error_returns_500_and_minus_32006(
    client: TestClient,
    mock_auth: MagicMock,
):
    """认证内部错误返回 HTTP 500 与 JSON-RPC -32006。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "认证服务内部错误",
            status_code=500,
            rpc_code=-32006,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-internal",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 500
    data = await resp.json()
    assert data["error"]["code"] == -32006


@pytest.mark.asyncio
async def test_post_rpc_challenge_headers_forwarded(
    client: TestClient,
    mock_auth: MagicMock,
):
    """401 响应应转发 WWW-Authenticate 与 Accept-Signature 头。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID WBA 签名无效",
            status_code=401,
            rpc_code=-32001,
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"',
                "Accept-Signature": 'sig1=("@method")',
                "X-Internal": "should-not-forward",
            },
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-challenge",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    assert resp.headers.get("WWW-Authenticate") == 'Bearer error="invalid_token"'
    assert resp.headers.get("Accept-Signature") == 'sig1=("@method")'
    assert "X-Internal" not in resp.headers
```

- [ ] **Step 5.2: 运行测试确认失败**

```bash
cd plugins/anp-agent
python -m pytest tests/test_server.py -v
```

Expected: 部分 FAIL（新测试期望 -32003/-32004/-32005/-32006/challenge 头，当前未实现）。

- [ ] **Step 5.3: 实现 server.py 更新**

在 `plugins/anp-agent/server.py` 中：

1. 新增常量（在 `_ERROR_DID_UNRESOLVABLE` 之后）：

```python
_ERROR_MISSING_AUTH = -32003
_ERROR_INVALID_DID_DOCUMENT = -32004
_ERROR_UNAUTHORIZED_VERIFICATION_METHOD = -32005
_ERROR_INTERNAL_AUTH = -32006
```

2. 替换 `_map_auth_error`：

```python
def _map_auth_error(
    exc: AuthenticationError,
) -> tuple[ANPRPCError, dict[str, str] | None]:
    """将结构化认证异常映射为 JSON-RPC / HTTP 错误。

    直接读取 AuthenticationError 携带的元数据，不再反向解析异常字符串。
    """
    challenge_headers: dict[str, str] | None = None
    if exc.status_code == 401 and exc.headers:
        challenge_headers = {
            name: value
            for name, value in exc.headers.items()
            if name.lower() in ("www-authenticate", "accept-signature")
        }

    return (
        ANPRPCError(
            http_status=exc.status_code,
            rpc_code=exc.rpc_code,
            message=str(exc),
        ),
        challenge_headers,
    )
```

3. 更新 `_handle_rpc` 中的认证失败处理：

```python
    except AuthenticationError as exc:
        err, challenge_headers = _map_auth_error(exc)
        return web.json_response(
            _jsonrpc_error(rpc_id, err.rpc_code, err.message),
            status=err.http_status,
            headers=challenge_headers,
        )
```

- [ ] **Step 5.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_server.py -v
```

Expected: PASS。

- [ ] **Step 5.5: 提交**

```bash
git add plugins/anp-agent/server.py plugins/anp-agent/tests/test_server.py
git commit -m "feat(server): 使用结构化 AuthenticationError 映射错误码并转发 challenge 头"
```

---

### Task 6: 更新现有测试中的断言

**Files:**
- Modify: `plugins/anp-agent/tests/test_auth.py`, `plugins/anp-agent/tests/test_server.py`, `plugins/anp-agent/tests/test_integration.py`
- Test: 上述文件

**Interfaces:**
- Consumes: 新的 `AuthenticationError` 字段与分类器行为
- Produces: 测试断言与新行为一致。

- [ ] **Step 6.1: 更新 test_auth.py**

`test_unresolvable_did_raises` 改为使用 `DidWbaVerifierError`：

```python
@pytest.mark.asyncio
async def test_unresolvable_did_raises(identity: ANPIdentity) -> None:
    """DID 文档无法解析时应抛出 -32002。"""
    from anp.authentication.did_wba_verifier import DidWbaVerifierError

    original_resolver = resolve_did_wba_document

    async def _failing_resolver(did: str, verify_proof: bool = False):
        raise DidWbaVerifierError(
            "Failed to resolve DID document: mocked failure",
            status_code=401,
        )

    did_wba_verifier_module.resolve_did_wba_document = _failing_resolver

    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32002
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
```

`test_did_resolution_timeout_returns_unresolvable_error` 更新断言：

```python
        ...
        assert exc_info.value.rpc_code == -32002
        ...
```

- [ ] **Step 6.2: 更新 test_server.py**

替换 `test_post_rpc_unresolvable_did_returns_401_and_minus_32002` 为结构化构造：

```python
@pytest.mark.asyncio
async def test_post_rpc_unresolvable_did_returns_401_and_minus_32002(
    client: TestClient,
    mock_auth: MagicMock,
):
    """DID 无法解析返回 HTTP 401 与 JSON-RPC -32002。"""
    mock_auth.authenticate = AsyncMock(
        side_effect=AuthenticationError(
            "DID 文档无法解析",
            status_code=401,
            rpc_code=-32002,
        )
    )

    payload = {
        "jsonrpc": "2.0",
        "method": "chat",
        "params": {"message": "你好"},
        "id": "req-unresolvable",
    }
    resp = await client.post("/agent/rpc", data=json.dumps(payload))

    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32002
```

- [ ] **Step 6.3: 更新 test_integration.py**

将 `test_rpc_without_signature_returns_401` 的断言更新：

```python
    assert resp.status == 401
    data = await resp.json()
    assert data["error"]["code"] == -32003
    assert data["error"]["message"] == "缺少认证头"
```

- [ ] **Step 6.4: 运行测试确认通过**

```bash
cd plugins/anp-agent
python -m pytest tests/test_auth.py tests/test_server.py tests/test_integration.py -v
```

Expected: PASS。

- [ ] **Step 6.5: 提交**

```bash
git add plugins/anp-agent/tests/test_auth.py plugins/anp-agent/tests/test_server.py plugins/anp-agent/tests/test_integration.py
git commit -m "test: 更新认证错误分类相关断言"
```

---

### Task 7: 运行 lint、格式化与覆盖率

**Files:**
- 全部改动文件

**Interfaces:**
- 无

- [ ] **Step 7.1: 运行 ruff 与 black**

```bash
cd plugins/anp-agent
ruff check .
black --check .
```

Expected: 全部通过。如有问题，运行 `ruff check --fix .` 或 `black .` 后重新检查。

- [ ] **Step 7.2: 运行完整测试套件并检查覆盖率**

```bash
cd plugins/anp-agent
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

Expected: 覆盖率 ≥ 85%，测试全部通过。

- [ ] **Step 7.3: 提交**

```bash
git add .
git commit -m "chore: 通过 lint、格式化与覆盖率检查"
```

---

### Task 8: 手动回归验证

**Files:**
- 无（手动验证）

**Interfaces:**
- 无

- [ ] **Step 8.1: 启动 DID 文档服务器**

```bash
cd scripts
python3 start_did_server.py
```

- [ ] **Step 8.2: 启动 Hermes gateway**

在另一个终端：

```bash
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
hermes run
```

- [ ] **Step 8.3: 合法签名请求返回 result**

```bash
cd scripts
export ANP_ENDPOINT=http://localhost:8900
python3 anp_chat_client.py "你好"
```

Expected: 返回 Hermes 回复文本，无 error。

- [ ] **Step 8.4: 未配置 resolver 返回 -32002**

停止 Hermes，不设置 `ANP_DID_RESOLVER_BASE_URL` 重新启动，然后发送请求：

```bash
export ANP_ALLOW_ALL_USERS=1
hermes run
```

```bash
cd scripts
python3 anp_chat_client.py "你好"
```

Expected: 响应包含 `error.code == -32002`，消息为 `DID 文档无法解析`。

- [ ] **Step 8.5: 不带签名头返回 -32003**

由于 `anp_chat_client.py` 始终会签名，临时用 curl 发送无签名请求：

```bash
curl -X POST http://localhost:8900/agent/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"chat","params":{"message":"你好"},"id":"1"}'
```

Expected: HTTP 401，响应体 `error.code == -32003`，消息 `缺少认证头`。

- [ ] **Step 8.6: 记录结果**

根据回归结果在 PR 描述中说明：
- 合法签名：通过
- 缺少 resolver：`-32002`
- 缺少签名头：`-32003`

---

## Self-Review Checklist

- [x] **Spec coverage:** 6 个错误码均对应到 Task 2/3/5；challenge 头转发对应 Task 5；resolver 网络错误修复对应 Task 4；测试更新对应 Task 6/7。
- [x] **Placeholder scan:** 无 TBD/TODO/implement later；所有步骤包含完整代码与命令。
- [x] **Type consistency:** `AuthenticationError` 字段名（`status_code`, `rpc_code`, `headers`）在所有 task 中保持一致；`_map_auth_error` 返回类型保持一致。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-05-refactor-anp-auth-error-handling.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
