# anp-rpc-bridge Specification

## Purpose

定义 `anp-agent` 插件的 JSON-RPC 调用桥接能力：在 `/agent/rpc` 接收请求，完成 DID WBA 认证，将通过认证的调用转换为 Hermes `MessageEvent`，并把 Hermes 回复封装为 JSON-RPC 2.0 响应。

## Requirements

### Requirement: JSON-RPC 请求接收
插件 SHALL 暴露 `POST /agent/rpc`，只接收单个 JSON-RPC 2.0 请求对象，并在进入认证与处理流程前完成基础请求校验。

#### Scenario: 有效 JSON-RPC 请求
- **WHEN** 调用方发送 `POST /agent/rpc` 且 body 为合法 JSON-RPC 2.0 对象，请求包含 `jsonrpc: "2.0"`、非空字符串 `id`、字符串 `method` 和对象 `params`
- **THEN** 插件解析 `method`、`params`、`id` 并进入认证与处理流程

#### Scenario: 拒绝 batch 请求
- **WHEN** 调用方发送 JSON array 形式的 batch 请求
- **THEN** 插件返回 HTTP 400，JSON-RPC `error.code` 为 `-32600`，响应 `id` 为 `null`，且不进入认证与 Hermes 处理流程

#### Scenario: 拒绝 notification 请求
- **WHEN** 调用方发送缺少 `id` 的 JSON-RPC 请求
- **THEN** 插件返回 HTTP 400，JSON-RPC `error.code` 为 `-32600`，响应 `id` 为 `null`，且不进入认证与 Hermes 处理流程

#### Scenario: 拒绝无效 jsonrpc 版本
- **WHEN** 调用方发送缺少 `jsonrpc` 或 `jsonrpc` 不等于 `"2.0"` 的请求
- **THEN** 插件返回 HTTP 400，JSON-RPC `error.code` 为 `-32600`；若请求包含合法非空字符串 `id` 则响应 `id` 回显该值，否则响应 `id` 为 `null`

#### Scenario: 拒绝非字符串或空字符串 id
- **WHEN** 调用方发送 `id` 为数字、对象、数组、null 或空字符串的请求
- **THEN** 插件返回 HTTP 400，JSON-RPC `error.code` 为 `-32600`，响应 `id` 为 `null`，且不进入认证与 Hermes 处理流程

#### Scenario: 拒绝无效 method 或 params
- **WHEN** 调用方发送非字符串 `method` 或非对象 `params`
- **THEN** 插件返回 HTTP 400，JSON-RPC `error.code` 为 `-32600`；若请求包含合法非空字符串 `id` 则响应 `id` 回显该值，否则响应 `id` 为 `null`

#### Scenario: 接收 Core Binding params envelope
- **WHEN** 调用方发送合法 JSON-RPC 2.0 请求，且 `params` 为包含 `meta` 与 `body` 的 Core Binding envelope
- **THEN** 插件在认证后按 Core Binding 规则校验 `meta` 与 `body`，并继续方法路由

### Requirement: DID WBA 身份认证
插件 SHALL 在 `/agent/rpc` 上验证调用方的 DID WBA HTTP Message Signature，拒绝未通过认证的请求。

#### Scenario: 合法签名
- **WHEN** 调用方使用有效的 DID 文档和私钥生成 HTTP Signature 头
- **THEN** 插件通过 `DidWbaVerifier` 或等效逻辑验证签名，并继续处理

#### Scenario: 非法签名
- **WHEN** 调用方签名无效、缺少签名头或 DID 无法解析
- **THEN** 插件返回 HTTP 401 或等效错误，不进入 Hermes 处理流程

### Requirement: 桥接到 Hermes 消息处理
插件 SHALL 将验证通过的 JSON-RPC 请求转换为 Hermes `MessageEvent`，并通过 `handle_message(event)` 交给 Hermes Agent Core 处理。桥接层 SHALL 使用服务端内部 request id 关联 Hermes 会话与 pending Future，而不是将客户端 JSON-RPC `id` 直接作为全局 pending key。

#### Scenario: 构造 MessageEvent
- **WHEN** 认证通过后
- **THEN** 使用调用方 DID 作为 `user_id`，服务端内部 request id 构造 `anp:{request_id}` 形式的 `chat_id`，构建 `MessageEvent` 并调用 `handle_message`

#### Scenario: 保留客户端 JSON-RPC id 元数据
- **WHEN** 桥接层构造 `MessageEvent`
- **THEN** 事件元数据包含客户端 JSON-RPC `id` 和服务端内部 request id，供追踪与调试使用

#### Scenario: 保留 Core Binding params 元数据
- **WHEN** 桥接层构造来自 Core Binding envelope 的 `MessageEvent`
- **THEN** 事件元数据保留原始 `params`，包括 `meta` 与 `body`

#### Scenario: 相同客户端 id 可并发处理
- **WHEN** 两个已认证调用使用相同的客户端 JSON-RPC `id` 并发调用 `chat`
- **THEN** 桥接层为每个调用分配不同的内部 request id，两个 pending Future 互不覆盖

### Requirement: 异步响应桥接
插件 SHALL 使用 asyncio Future 等待 Hermes 回复，并将成功回复封装为 JSON-RPC 2.0 成功响应；超时、取消、handler 异常和 pending 容量耗尽 SHALL 返回 JSON-RPC error，而不是成功 `result.response`。

#### Scenario: 正常回复
- **WHEN** Hermes 通过 `send()` 返回文本回复
- **THEN** Future 被设置结果，插件返回 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`，其中 `id` 回显客户端 JSON-RPC `id`

#### Scenario: 处理超时
- **WHEN** Hermes 在配置的超时时间内未返回回复
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示处理超时

#### Scenario: 处理取消
- **WHEN** bridge 停止或 pending Future 被取消
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示请求已取消

#### Scenario: 外部取消保持 asyncio 取消语义
- **WHEN** 当前请求处理协程被 aiohttp 或上层任务取消，且不是 pending Future 自身取消
- **THEN** bridge 不将该取消包装为业务 JSON-RPC 错误，而是继续传播 `asyncio.CancelledError`

#### Scenario: handler 提交失败
- **WHEN** `handle_message(event)` 抛出异常，导致请求无法提交给 Hermes
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示无法将请求提交给 Hermes 或内部错误

#### Scenario: pending 容量耗尽
- **WHEN** 当前 pending Future 数量已达到上限
- **THEN** 返回 JSON-RPC error，错误码 `-32603`，消息提示服务繁忙或内部错误

### Requirement: ANP 方法路由
插件 SHALL 在 `/agent/rpc` 中支持当前声明的 ANP JSON-RPC 方法，并对未知方法返回 JSON-RPC method not found。除基础方法 `chat` 与 `anp.get_capabilities` 外，插件 SHALL 只在 tool RPC 显式开启且方法对应 allowlisted Hermes tool 时路由 `hermes.tool.*` 方法。

#### Scenario: chat 方法
- **WHEN** 调用方发送合法且认证通过的 `chat` 请求
- **THEN** 插件将请求桥接到 Hermes 并返回 `result.response`

#### Scenario: anp.get_capabilities 方法
- **WHEN** 调用方发送合法且认证通过的 `anp.get_capabilities` 请求
- **THEN** 插件返回当前运行时 ANP 能力，不调用 Hermes message handler

#### Scenario: allowlisted Hermes tool 方法
- **WHEN** 调用方发送合法且认证通过的 `hermes.tool.<tool_name>` 请求
- **AND** tool RPC 已启用
- **AND** `<tool_name>` 对应当前 allowlisted、未 denylisted 且可用的 Hermes tool
- **THEN** 插件校验 params 后执行该 Hermes tool，并返回 JSON-RPC 成功响应

#### Scenario: 未授权 Hermes tool 方法
- **WHEN** 调用方发送合法且认证通过的 `hermes.tool.<tool_name>` 请求
- **AND** tool RPC 未启用，或 `<tool_name>` 未通过 allowlist/denylist/caller DID 授权
- **THEN** 插件返回 JSON-RPC error，错误码 `-32601`
- **AND** 不执行对应 Hermes tool

#### Scenario: 未知方法
- **WHEN** 调用方发送合法且认证通过但未被插件支持的方法名
- **THEN** 插件返回 JSON-RPC error，错误码 `-32601`

### Requirement: RPC bridge 错误路径测试覆盖
插件测试体系 SHALL 对 `/agent/rpc` 和 `ANPBridge` 的关键错误路径提供回归测试，确保错误仍以 JSON-RPC error 返回而不是成功 `result.response`。

#### Scenario: JSON-RPC invalid request 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 batch、notification、无效 `jsonrpc`、无效 `id`、无效 `method` 和无效 `params` 请求均返回 HTTP 400 与 JSON-RPC `-32600`

#### Scenario: bridge 内部错误测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖处理超时、pending Future 取消、handler 提交异常和 pending 容量耗尽均返回 JSON-RPC `-32603` error

#### Scenario: 并发 request id 隔离测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖两个相同客户端 JSON-RPC `id` 的并发请求会分配不同内部 request id，且响应互不串扰

### Requirement: Core Binding 与能力协商测试覆盖
插件测试体系 SHALL 对当前已声明的 Core Binding envelope、`anp.get_capabilities` 行为以及可选 Hermes tool RPC 能力提供回归测试。

#### Scenario: Core Binding envelope 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `chat` 可从合法 `params.body.message` 读取消息，并拒绝 unsupported profile、unsupported security profile 和 invalid envelope shape

#### Scenario: capabilities 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `anp.get_capabilities` 返回 service DID、supported profiles、supported security profiles、limits 和 supported content types，且不调用 Hermes message handler

#### Scenario: tool RPC 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 tool RPC 默认关闭、allowlisted 工具成功调用、未授权工具返回 `-32601`、参数无效返回 `-32602`、工具执行失败返回 JSON-RPC error

### Requirement: 不实现支付与加密
本期插件 SHALL 不实现 AP2 支付验证和 E2EE 加密，仅保证身份认证和明文 JSON-RPC 通信。

#### Scenario: 收到支付字段
- **WHEN** JSON-RPC params 中包含支付相关字段
- **THEN** 插件忽略该字段，不触发任何支付验证逻辑
