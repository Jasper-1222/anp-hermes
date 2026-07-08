## MODIFIED Requirements

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
