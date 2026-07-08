## ADDED Requirements

### Requirement: JSON-RPC 成功响应契约
当 `/agent/rpc` 请求通过 DID WBA 认证并被 Hermes 成功处理时，适配器 SHALL 返回 JSON-RPC 2.0 成功响应，并安全附带认证成功响应头。

#### Scenario: chat 成功响应
- **WHEN** 调用方发送合法且认证通过的 `chat` JSON-RPC 请求，且 Hermes 返回文本回复
- **THEN** HTTP 状态码为 200，响应体为 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`

#### Scenario: 成功响应附带 Authentication-Info
- **WHEN** 认证器为成功认证生成 `Authentication-Info` 响应头
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应包含该 `Authentication-Info` 头

#### Scenario: 成功响应不透传未允许头
- **WHEN** 认证器成功结果包含未列入允许列表的响应头
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应不包含这些未允许头
