## MODIFIED Requirements

### Requirement: 运行时能力声明
适配器 SHALL 在运行时能力响应和 OpenRPC 文档中声明当前真实支持且已启用的 ANP Core Binding 与可选 Hermes tool RPC 能力，不得声明尚未实现的 Direct、Group 或 E2EE 能力。Hermes tools 方法只有在 tool RPC 显式开启且对应工具通过 allowlist、denylist、caller DID 授权和可用性校验时才可声明。

#### Scenario: 仅声明已支持 profiles
- **WHEN** 插件返回 `anp.get_capabilities`
- **THEN** `supported_profiles` 包含 `anp.core.binding.v1`，且不包含尚未实现的 Direct、Group 或 E2EE profile

#### Scenario: 默认不声明 Hermes tools 方法
- **WHEN** tool RPC 未启用或没有 allowlisted 可用工具
- **THEN** OpenRPC methods 列表不包含任何 `hermes.tool.*` 方法

#### Scenario: 声明已启用 Hermes tools 方法
- **WHEN** tool RPC 已启用且存在 allowlisted、未 denylisted、caller DID 授权且当前可用的 Hermes tool
- **THEN** OpenRPC methods 列表可以包含对应 `hermes.tool.<tool_name>` 方法
- **AND** 不包含未 allowlist、denylisted、未授权或当前不可用的工具方法
