## MODIFIED Requirements

### Requirement: JSON-RPC 成功响应契约
当 `/agent/rpc` 请求通过 DID WBA 认证并被 Hermes 成功处理，或被插件内置 ANP 方法成功处理时，适配器 SHALL 返回 JSON-RPC 2.0 成功响应，并安全附带认证成功响应头；当 bridge 处理失败时，适配器 SHALL 返回 JSON-RPC error 而不是成功响应。

#### Scenario: chat 成功响应
- **WHEN** 调用方发送合法且认证通过的 `chat` JSON-RPC 请求，且 Hermes 返回文本回复
- **THEN** HTTP 状态码为 200，响应体为 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`，其中 `id` 回显客户端 JSON-RPC `id`

#### Scenario: anp.get_capabilities 成功响应
- **WHEN** 调用方发送合法且认证通过的 `anp.get_capabilities` 请求
- **THEN** HTTP 状态码为 200，响应体为 JSON-RPC 成功响应，`result` 包含当前运行时能力信息

#### Scenario: 成功响应附带 Authentication-Info
- **WHEN** 认证器为成功认证生成 `Authentication-Info` 响应头，且请求被成功处理
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

## ADDED Requirements

### Requirement: 运行时能力声明
适配器 SHALL 在运行时能力响应和 OpenRPC 文档中声明当前真实支持的 ANP Core Binding 能力，不得声明尚未实现的 Direct、Group、E2EE 或 Hermes tools 方法。

#### Scenario: 仅声明已支持 profiles
- **WHEN** 插件返回 `anp.get_capabilities`
- **THEN** `supported_profiles` 包含 `anp.core.binding.v1`，且不包含尚未实现的 Direct、Group 或 E2EE profile

#### Scenario: 仅声明已支持方法
- **WHEN** 插件返回 OpenRPC 文档
- **THEN** methods 列表只包含当前已实现的方法，不包含尚未实现的 Hermes tools 或 Direct/Group 方法
