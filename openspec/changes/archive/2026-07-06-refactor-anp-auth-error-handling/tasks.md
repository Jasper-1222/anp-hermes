## 1. 重构 AuthenticationError 与分类器

- [x] 1.1 在 `plugins/anp-agent/auth.py` 中重构 `AuthenticationError`，添加 `status_code`、`rpc_code`、`headers`、`cause` 字段与默认错误码。
- [x] 1.2 新增 `_classify_verifier_error(exc: DidWbaVerifierError) -> tuple[str, int, int]`，按 `exc.message` 与 `status_code` 映射到 6 个错误码，未知错误保守回退。
- [x] 1.3 更新 `ANPAuth.authenticate`：`DidWbaVerifierError` 走分类器；`asyncio.TimeoutError` / `aiohttp.ClientError` 映射为 `-32002`；未预期异常记录日志后映射为 `-32006`。
- [x] 1.4 更新 `_make_resolver_wrapper`，在 base_url 覆盖路径下将 `aiohttp.ClientError` 与 `asyncio.TimeoutError` 包装为 `DidWbaVerifierError("Failed to resolve DID document: ...", status_code=401)`。

## 2. 更新 server.py 错误映射

- [x] 2.1 在 `plugins/anp-agent/server.py` 新增常量 `_ERROR_MISSING_AUTH` (-32003)、`_ERROR_INVALID_DID_DOCUMENT` (-32004)、`_ERROR_UNAUTHORIZED_VERIFICATION_METHOD` (-32005)、`_ERROR_INTERNAL_AUTH` (-32006)。
- [x] 2.2 重写 `_map_auth_error(exc)`，直接读取 `AuthenticationError` 的 `rpc_code`、`status_code`、`message`，返回 `(ANPRPCError, challenge_headers | None)`。
- [x] 2.3 在 `_map_auth_error` 中仅当 `status_code == 401` 时转发 `WWW-Authenticate` 和 `Accept-Signature` 头。
- [x] 2.4 更新 `_handle_rpc`，将 challenge headers 传入 `web.json_response(..., headers=...)`。

## 3. 更新测试

- [x] 3.1 更新 `plugins/anp-agent/tests/test_auth.py`：为每种失败场景断言 `rpc_code`；新增 resolver 网络错误、DID 文档无效、认证方法未授权、内部错误测试。
- [x] 3.2 更新 `plugins/anp-agent/tests/test_server.py`：新增 `-32003`、`-32004`、`-32005`、`-32006` 的 HTTP/JSON-RPC 映射测试；新增 challenge headers 转发测试。
- [x] 3.3 更新 `plugins/anp-agent/tests/test_integration.py`：将 `test_rpc_without_signature_returns_401` 的断言更新为 `-32003 缺少认证头`。

## 4. 验证

- [x] 4.1 运行 `ruff check .` 与 `black --check .` 通过。
- [x] 4.2 运行 `python -m pytest tests/test_auth.py tests/test_server.py tests/test_integration.py -v` 全部通过。
- [x] 4.3 运行 `python -m pytest tests/ --cov=. --cov-fail-under=85 -q` 通过。
- [x] 4.4 手动回归：合法签名请求返回 result；未配置/错误配置 `ANP_DID_RESOLVER_BASE_URL` 返回 `-32002`；不带签名头返回 `-32003`。
