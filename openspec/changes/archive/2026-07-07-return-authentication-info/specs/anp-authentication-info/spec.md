## ADDED Requirements

### Requirement: 成功认证返回 Authentication-Info
插件 SHALL 在 DID WBA HTTP Message Signatures 认证成功且 verifier 生成 `Authentication-Info` 时，将该响应头返回给调用方。

#### Scenario: 成功认证响应携带 Authentication-Info
- **WHEN** `/agent/rpc` 请求通过 DID WBA HTTP Message Signatures 认证，且认证器生成 `Authentication-Info` 响应头
- **THEN** HTTP 200 JSON-RPC 成功响应包含同名 `Authentication-Info` 头

#### Scenario: 无认证响应头时不返回空头
- **WHEN** `/agent/rpc` 请求认证成功但认证器未生成 `Authentication-Info` 响应头
- **THEN** HTTP 响应不包含空的 `Authentication-Info` 头

### Requirement: 成功认证响应头过滤
插件 SHALL 只转发明确允许的成功认证响应头，不得将 verifier 返回的任意响应头透传给调用方。

#### Scenario: 仅转发 Authentication-Info
- **WHEN** verifier 成功认证结果包含 `Authentication-Info`、`Authorization` 与其他内部响应头
- **THEN** `/agent/rpc` 成功响应只包含允许的 `Authentication-Info` 头，不包含响应 `Authorization` 或内部头
