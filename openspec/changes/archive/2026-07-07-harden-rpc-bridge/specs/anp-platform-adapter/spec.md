## MODIFIED Requirements

### Requirement: send 桥接
适配器 SHALL 实现 `send(chat_id, content, ...)`，当 `chat_id` 以 `anp:` 前缀标识某次 JSON-RPC 调用的服务端内部 request id 时，将该调用标记为已完成并返回结果。

#### Scenario: 回复 ANP 调用
- **WHEN** Hermes 处理完 ANP 调用并通过 `send()` 向 `anp:{request_id}` 形式的 `chat_id` 发送回复
- **THEN** 适配器提取服务端内部 request id，并将对应的 JSON-RPC pending Future 设置为该回复内容

#### Scenario: 未知 request id 回复失败
- **WHEN** Hermes 通过 `send()` 回复的 `anp:{request_id}` 不存在或已完成
- **THEN** 适配器返回失败结果，不创建新的 pending Future

#### Scenario: 非 ANP chat_id 回复失败
- **WHEN** Hermes 通过 `send()` 回复的 `chat_id` 不以 `anp:` 为前缀
- **THEN** 适配器返回失败结果，不影响任何 ANP pending Future

### Requirement: JSON-RPC 成功响应契约
当 `/agent/rpc` 请求通过 DID WBA 认证并被 Hermes 成功处理时，适配器 SHALL 返回 JSON-RPC 2.0 成功响应，并安全附带认证成功响应头；当 bridge 处理失败时，适配器 SHALL 返回 JSON-RPC error 而不是成功响应。

#### Scenario: chat 成功响应
- **WHEN** 调用方发送合法且认证通过的 `chat` JSON-RPC 请求，且 Hermes 返回文本回复
- **THEN** HTTP 状态码为 200，响应体为 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`，其中 `id` 回显客户端 JSON-RPC `id`

#### Scenario: 成功响应附带 Authentication-Info
- **WHEN** 认证器为成功认证生成 `Authentication-Info` 响应头，且 Hermes 成功返回文本回复
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应包含该 `Authentication-Info` 头

#### Scenario: 成功响应不透传未允许头
- **WHEN** 认证器成功结果包含未列入允许列表的响应头
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应不包含这些未允许头

#### Scenario: bridge 失败不返回成功响应
- **WHEN** 请求通过认证但 bridge 超时、取消或无法提交给 Hermes
- **THEN** `/agent/rpc` 返回 JSON-RPC `error`，响应体不包含 `result.response`

#### Scenario: bridge 失败不附带成功认证头
- **WHEN** 请求通过认证并生成 `Authentication-Info`，但 bridge 处理失败
- **THEN** `/agent/rpc` 的错误响应不包含成功认证 `Authentication-Info` 头
