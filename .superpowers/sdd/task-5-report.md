# Task 5 报告：DID WBA 签名 chat

## RED 失败命令 / 摘要

- 命令：`python3 -m pytest clients/anp-client/tests/test_chat.py -q`
- 结果：按预期失败，收集阶段报错：`ImportError: cannot import name 'build_chat_body' from 'anp_client'`。
- 结论：新增测试确实覆盖了尚未实现的签名/chat helper，满足先 RED 再实现。

## 实现摘要

- `clients/anp-client/scripts/signing.py`
  - 新增 `build_signed_headers(identity, target_url, body)`。
  - 使用 ANP SDK `anp.authentication.DIDWbaAuthHeader` 生成 DID WBA HTTP Signature 请求头，包含 `Signature`、`Signature-Input` 与 `Content-Type: application/json`。
- `clients/anp-client/scripts/anp_client.py`
  - 新增 `build_chat_body()`，构造 Phase 1 legacy JSON-RPC `method=chat` 与 `params.message` body。
  - 新增 `format_rpc_error()`，为常见服务端 JSON-RPC 错误码 `-32002/-32001/-32003` 输出中文排障提示。
  - 新增 `chat_service()`：调用 `discover_service(..., require_chat=True)`，复用 Task 4 endpoint 安全策略，仅通过签名 POST 调用服务智能体 RPC。
  - 新增 `_cmd_chat()` 并接入 `main()`，支持普通输出与 `--json` 输出；`ClientError` 继续由 CLI 顶层捕获，避免 traceback。
  - HTTP redirect、非 2xx、连接/超时、非 JSON、JSON-RPC error、缺少 `result.response` 均映射为 `ClientError`。
- `clients/anp-client/tests/test_chat.py`
  - 覆盖签名头、legacy chat body、错误码提示、成功 chat、JSON-RPC error、连接失败、未声明 chat 方法、RPC HTTP status、RPC 非 JSON、CLI 普通输出/JSON 输出、CLI 错误无 traceback。
  - 本地 aiohttp mock 使用 `TCPSite(..., port=0)`，避免端口 TOCTOU。

## GREEN 命令 / 结果

- `python3 -m pytest clients/anp-client/tests/test_chat.py -q`：`14 passed in 0.19s`
- `python3 -m pytest clients/anp-client/tests -q`：`75 passed in 2.90s`
- `python3 -m black --check clients/anp-client/scripts/anp_client.py clients/anp-client/scripts/signing.py clients/anp-client/tests/test_chat.py`：`3 files would be left unchanged.`
- `python3 -m ruff check clients/anp-client/scripts/anp_client.py clients/anp-client/scripts/signing.py clients/anp-client/tests/test_chat.py`：`All checks passed!`
- `git diff --check`：通过，无输出。

## 自审结果

- 已确认 `chat_service()` 调用 `discover_service(..., require_chat=True)`，不会对未声明 `chat` 的服务发起 RPC。
- 已确认 URL 安全沿用 Task 4 `ensure_allowed_url()`，只允许 loopback HTTP 与 HTTPS。
- 已确认签名使用 ANP SDK DID WBA 能力，没有伪造自定义签名格式。
- 已确认 Phase 1 仅使用 legacy `params.message`，未实现 Core Binding envelope、地址簿、AP2、E2EE、工具 RPC、群聊或多轮会话同步。
- Simplify & Harden 自审：未发现需要结构性重构或安全补丁的问题；仅发现格式化问题，已用 Black 修正并重跑验证。
- 自愈记录：已在 `.learnings/HEALS.md` 记录本任务中修复的 pytest async 测试形态问题与 Black 格式化问题。

## Commit hash

- `efcfa94` (`feat: 实现 DID WBA 签名 chat 调用`)

## Concerns

- 无阻塞 concerns。
- 当前签名集成依赖本地已安装的 ANP SDK `DIDWbaAuthHeader` API；本环境已通过测试验证该 API 可用。
