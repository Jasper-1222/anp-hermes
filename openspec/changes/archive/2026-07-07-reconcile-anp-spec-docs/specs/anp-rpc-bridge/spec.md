## MODIFIED Requirements

### Requirement: 异步响应桥接
插件 SHALL 使用 asyncio Future 等待 Hermes 回复，并将回复封装为 JSON-RPC 2.0 响应返回。

#### Scenario: 正常回复
- **WHEN** Hermes 通过 `send()` 返回文本回复
- **THEN** Future 被设置结果，插件返回 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`

#### Scenario: 处理超时
- **WHEN** Hermes 在配置的超时时间内未返回回复
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示处理超时
