## ADDED Requirements

### Requirement: JSON-RPC 请求接收
插件 SHALL 暴露 `POST /agent/rpc`，接收符合 JSON-RPC 2.0 规范的请求体。

#### Scenario: 有效 JSON-RPC 请求
- **WHEN** 调用方发送 `POST /agent/rpc` 且 body 为合法 JSON-RPC 2.0 请求
- **THEN** 插件解析 `method`、`params`、`id` 并进入认证与处理流程

### Requirement: DID WBA 身份认证
插件 SHALL 在 `/agent/rpc` 上验证调用方的 DID WBA HTTP Message Signature，拒绝未通过认证的请求。

#### Scenario: 合法签名
- **WHEN** 调用方使用有效的 DID 文档和私钥生成 HTTP Signature 头
- **THEN** 插件通过 `DidWbaVerifier` 或等效逻辑验证签名，并继续处理

#### Scenario: 非法签名
- **WHEN** 调用方签名无效、缺少签名头或 DID 无法解析
- **THEN** 插件返回 HTTP 401 或等效错误，不进入 Hermes 处理流程

### Requirement: 桥接到 Hermes 消息处理
插件 SHALL 将验证通过的 JSON-RPC 请求转换为 Hermes `MessageEvent`，并通过 `handle_message(event)` 交给 Hermes Agent Core 处理。

#### Scenario: 构造 MessageEvent
- **WHEN** 认证通过后
- **THEN** 使用调用方 DID 作为 `user_id`，`anp:{rpc_id}` 作为 `chat_id`，构建 `MessageEvent` 并调用 `handle_message`

### Requirement: 异步响应桥接
插件 SHALL 使用 asyncio Future 等待 Hermes 回复，并将回复封装为 JSON-RPC 2.0 响应返回。

#### Scenario: 正常回复
- **WHEN** Hermes 通过 `send()` 返回文本回复
- **THEN** Future 被设置结果，插件返回 `{"jsonrpc":"2.0","result":"...","id":...}`

#### Scenario: 处理超时
- **WHEN** Hermes 在配置的超时时间内未返回回复
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示处理超时

### Requirement: 不实现支付与加密
本期插件 SHALL 不实现 AP2 支付验证和 E2EE 加密，仅保证身份认证和明文 JSON-RPC 通信。

#### Scenario: 收到支付字段
- **WHEN** JSON-RPC params 中包含支付相关字段
- **THEN** 插件忽略该字段，不触发任何支付验证逻辑
