## Why

当前 `anp-agent` 已启用 DID WBA verifier 的 `emit_authentication_info_header=True`，但成功认证后的 `/agent/rpc` 响应没有把 SDK 产生的 `Authentication-Info` 头返回给调用方。补齐该响应头能让插件更符合 DID WBA HTTP Message Signatures 成功认证流程，并为后续调用方复用认证信息打基础。

## What Changes

- 在成功 DID WBA 认证后，从认证器获取安全的成功响应头并随 `/agent/rpc` 成功响应返回。
- 将认证结果从单一 caller DID 字符串扩展为结构化结果，包含调用方 DID 与可转发响应头。
- 仅转发 `Authentication-Info` 等明确允许的成功认证响应头，不暴露内部 verifier 细节或任意头。
- 保持认证失败时现有 JSON-RPC 错误码和 challenge 头转发行为不变。
- 增加认证与 server 单元测试，覆盖成功响应携带 `Authentication-Info`、无头时不返回空头、失败响应行为不回归。
- 更新 README / 插件 README / OpenSpec 状态说明，记录该能力边界。

## Capabilities

### New Capabilities

- `anp-authentication-info`：定义 DID WBA 成功认证后 `Authentication-Info` 响应头的生成、过滤与转发契约。

### Modified Capabilities

- `anp-platform-adapter`：`/agent/rpc` 成功响应行为需要增加安全认证响应头转发，同时保持 JSON-RPC result shape 不变。

## Impact

- 影响认证结果结构与调用点：`plugins/anp-agent/auth.py`、`plugins/anp-agent/server.py`。
- 影响测试：`plugins/anp-agent/tests/test_auth.py`、`plugins/anp-agent/tests/test_server.py`，必要时补充 E2E 断言。
- 影响文档：`README.md`、`plugins/anp-agent/README.md`、`docs/anp-hermes-openspec-execution-state.md`。
- 不引入新的外部依赖，不改变 DID WBA 身份生成、错误分类或 JSON-RPC result body。