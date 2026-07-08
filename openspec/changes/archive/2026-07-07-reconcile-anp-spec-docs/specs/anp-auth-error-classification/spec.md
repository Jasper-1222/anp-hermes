## MODIFIED Requirements

### Requirement: AuthenticationError 结构
`AuthenticationError` SHALL 携带 `status_code`、`rpc_code`、`message` 与 `headers`，供调用方无需重新解析字符串即可构造响应。

#### Scenario: 构造结构化异常
- **WHEN** 认证器检测到具体失败原因
- **THEN** 抛出包含正确 `status_code`、`rpc_code`、`message` 与可选 `headers` 的 `AuthenticationError`
