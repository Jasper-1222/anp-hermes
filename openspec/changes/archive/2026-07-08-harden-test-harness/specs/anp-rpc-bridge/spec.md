## ADDED Requirements

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
插件测试体系 SHALL 对当前已声明的 Core Binding envelope 与 `anp.get_capabilities` 行为提供回归测试。

#### Scenario: Core Binding envelope 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `chat` 可从合法 `params.body.message` 读取消息，并拒绝 unsupported profile、unsupported security profile 和 invalid envelope shape

#### Scenario: capabilities 测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `anp.get_capabilities` 返回 service DID、supported profiles、supported security profiles、limits 和 supported content types，且不调用 Hermes message handler