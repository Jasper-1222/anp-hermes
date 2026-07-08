## ADDED Requirements

### Requirement: Tool RPC 默认关闭
`anp-agent` SHALL 默认不向 ANP 调用方暴露任何 Hermes tools。只有当运行时配置显式开启 tool RPC 且至少配置允许的 tools 或 toolsets 时，插件才可以在发现文档、能力响应和 RPC 路由中暴露工具方法。

#### Scenario: 未配置 tool RPC
- **WHEN** 插件未配置 tool RPC 或 `tool_rpc.enabled` 为 false
- **THEN** `/agent/interface.json` 不包含任何 `hermes.tool.*` 方法
- **AND** `/agent/ad.json` 与 `anp.get_capabilities` 不声明 Hermes tools 能力
- **AND** `/agent/rpc` 对 `hermes.tool.*` 方法返回 JSON-RPC `-32601`

#### Scenario: 开启但未配置允许工具
- **WHEN** `tool_rpc.enabled` 为 true 但未配置 `allowed_tools` 或 `allowed_toolsets`
- **THEN** 插件仍不暴露任何 Hermes tools
- **AND** 不得把 Hermes 平台可见工具集自动全部暴露给 ANP 调用方

### Requirement: Tool RPC allowlist 与 denylist
`anp-agent` SHALL 使用显式 allowlist 控制可被 ANP 调用的 Hermes tools，并使用内置 denylist 阻止高风险工具被远程调用。denylist SHALL 优先于 allowlist。

#### Scenario: allowlisted 工具被声明
- **WHEN** tool RPC 已启用且工具通过 `allowed_tools` 或 `allowed_toolsets` 允许
- **AND** 该工具未命中内置或配置 denylist
- **AND** 该工具当前可用
- **THEN** 插件可以在 OpenRPC 文档中声明对应 `hermes.tool.<tool_name>` 方法

#### Scenario: denylisted 工具不被声明
- **WHEN** 某工具同时出现在 allowlist 和 denylist 中
- **THEN** denylist 优先生效
- **AND** 插件不得在 OpenRPC、Agent Description 或 capabilities 中声明该工具
- **AND** `/agent/rpc` 对应方法返回 JSON-RPC `-32601`

#### Scenario: 高风险工具默认拒绝
- **WHEN** 运维误将 shell、代码执行、文件写入、skill 管理、浏览器自动化、外部发布或未知副作用工具加入 allowlist
- **THEN** 插件 SHALL 通过内置高风险 denylist 默认拒绝这些工具
- **AND** 除非后续规格另行定义更严格的审批机制，否则不得通过 ANP tool RPC 暴露这些工具

### Requirement: Caller DID 授权
`anp-agent` SHALL 在工具调用前验证调用方已通过 DID WBA 认证，并按 tool RPC caller allowlist 决定该 DID 是否可以调用工具。

#### Scenario: 未授权 DID 调用工具
- **WHEN** 已认证调用方 DID 不在 tool RPC caller allowlist 中
- **AND** 该调用方请求 `hermes.tool.<tool_name>`
- **THEN** 插件返回 JSON-RPC `-32601`
- **AND** 不通过差异化错误泄露该工具是否存在或是否被配置

#### Scenario: 已授权 DID 调用 allowlisted 工具
- **WHEN** 已认证调用方 DID 在 tool RPC caller allowlist 中
- **AND** 请求的工具已通过 allowlist、denylist 和可用性校验
- **THEN** 插件进入工具参数校验与执行流程

### Requirement: OpenRPC 工具方法映射
`anp-agent` SHALL 将允许暴露的 Hermes registry tool name 映射为 `hermes.tool.<tool_name>` JSON-RPC method，并在 OpenRPC 文档中声明可测试的参数和返回结构。

#### Scenario: OpenRPC 包含工具方法
- **WHEN** tool RPC 已启用且存在可暴露工具 `example_tool`
- **THEN** `/agent/interface.json` 的 methods 包含 `hermes.tool.example_tool`
- **AND** 该方法的参数说明来源于 Hermes tool schema
- **AND** 方法描述说明该调用会执行 allowlisted Hermes tool

#### Scenario: 配置变更后 OpenRPC 反映当前能力
- **WHEN** 运维关闭 tool RPC 或移除某工具 allowlist
- **THEN** `/agent/interface.json` 不再声明对应 `hermes.tool.*` 方法

### Requirement: 工具参数校验
`anp-agent` SHALL 在执行 Hermes tool 前校验 JSON-RPC `params` 与该工具 schema 的兼容性。无效参数 SHALL 返回 JSON-RPC `-32602`，不得执行工具 handler。

#### Scenario: 工具参数合法
- **WHEN** 调用方请求 allowlisted `hermes.tool.<tool_name>` 且 `params` 符合工具 schema
- **THEN** 插件执行对应 Hermes tool

#### Scenario: 工具参数无效
- **WHEN** 调用方请求 allowlisted `hermes.tool.<tool_name>` 但 `params` 缺少必填字段或字段类型不匹配
- **THEN** 插件返回 JSON-RPC `-32602`
- **AND** 不执行对应 Hermes tool

### Requirement: 工具执行入口
`anp-agent` SHALL 通过 Hermes 高层工具调用入口执行 allowlisted 工具，并保留 Hermes tool middleware、hooks 与结果 transform；不得直接把远程请求透传到底层 registry dispatch。

#### Scenario: 工具执行复用 Hermes 调用入口
- **WHEN** 插件执行 allowlisted Hermes tool
- **THEN** 调用路径 SHALL 使用 Hermes 高层 tool invocation 入口或等效封装
- **AND** 不直接调用底层 registry dispatch 绕过 middleware 与 hooks

#### Scenario: 工具执行成功
- **WHEN** allowlisted Hermes tool 执行成功
- **THEN** `/agent/rpc` 返回 JSON-RPC 2.0 成功响应
- **AND** `result` 包含工具返回内容和安全的工具调用元数据

### Requirement: 工具错误与超时映射
`anp-agent` SHALL 将工具执行失败、超时、取消、结果过大和内部异常映射为结构化 JSON-RPC error，并避免泄露堆栈、内部路径、密钥或未授权工具信息。

#### Scenario: 工具执行失败
- **WHEN** allowlisted Hermes tool 执行失败
- **THEN** 插件返回 JSON-RPC `-32603`
- **AND** error message 为安全的对外错误消息

#### Scenario: 工具执行超时
- **WHEN** Hermes tool 未在配置的 tool RPC 超时时间内完成
- **THEN** 插件返回 JSON-RPC `-32603`
- **AND** error data 标识超时类别

#### Scenario: 工具结果过大
- **WHEN** Hermes tool 返回结果超过配置的最大结果大小
- **THEN** 插件返回 JSON-RPC `-32603`
- **AND** 不在响应中返回完整超大结果

### Requirement: 工具调用审计
`anp-agent` SHALL 为每次 tool RPC 调用记录安全审计信息，至少包含 caller DID、服务端 request id、客户端 JSON-RPC id、tool name、执行状态、错误类别和耗时。默认不得记录完整参数或完整结果。

#### Scenario: 成功工具调用被审计
- **WHEN** allowlisted Hermes tool 执行成功
- **THEN** 插件记录 caller DID、request id、tool name、成功状态和耗时
- **AND** 默认不记录完整参数或完整结果

#### Scenario: 失败工具调用被审计
- **WHEN** 工具调用因未授权、参数无效、执行失败或超时而失败
- **THEN** 插件记录 caller DID、request id、tool name 或请求 method、失败类别和耗时
- **AND** 不记录敏感参数或内部堆栈
