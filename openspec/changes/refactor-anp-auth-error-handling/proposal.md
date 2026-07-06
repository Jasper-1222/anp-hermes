## Why

当前 `anp-agent` 插件在 DID WBA 认证失败时，将所有错误统一包装为“认证失败”并仅通过子串匹配映射错误码，导致调用方无法区分签名无效、DID 文档解析失败、缺少认证头等场景。本次变更通过引入结构化认证错误分类与更具体的 JSON-RPC 错误码，提升可观测性与问题定位效率。

## What Changes

- 重构 `AuthenticationError`，携带 `status_code`、`rpc_code`、`headers` 与原始异常信息。
- 新增 `_classify_verifier_error()` 分类器，根据 `DidWbaVerifierError.message` 与 `status_code` 映射到 6 种错误码。
- 在 resolver wrapper 中将网络异常统一包装为 DID 文档解析失败，避免被误判为签名错误。
- 重写 `server.py` 的 `_map_auth_error()`，直接读取错误对象的元数据并转发安全的 challenge 头。
- 更新 `test_auth.py`、`test_server.py`、`test_integration.py` 以断言具体错误码与消息。

## Capabilities

### New Capabilities

- `anp-auth-error-classification`: 定义 ANP 插件认证失败时的错误分类与 JSON-RPC/HTTP 响应契约，包括 6 个错误码、对外消息、challenge 头转发规则与内部异常分类逻辑。

### Modified Capabilities

- `anp-platform-adapter`: 该能力的认证错误响应契约发生变化（新增具体错误码与消息），需要更新其相关行为要求。

## Impact

- `plugins/anp-agent/auth.py`
- `plugins/anp-agent/server.py`
- `plugins/anp-agent/tests/test_auth.py`
- `plugins/anp-agent/tests/test_server.py`
- `plugins/anp-agent/tests/test_integration.py`
- 调用方可见的 JSON-RPC `error.code` 与 `message` 将更具体（向下兼容：错误仍然存在，但 `code` 和 `message` 会变化）。
