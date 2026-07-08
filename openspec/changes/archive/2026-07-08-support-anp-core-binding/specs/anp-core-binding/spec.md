## ADDED Requirements

### Requirement: Core Binding 能力协商
插件 SHALL 支持 ANP Core Binding v1 的运行时能力协商方法 `anp.get_capabilities`，并返回当前运行时真实支持的 profiles、security profiles、service DID 与实现限制。

#### Scenario: 获取运行时能力
- **WHEN** 调用方通过 `/agent/rpc` 发送认证通过的 `anp.get_capabilities` JSON-RPC 请求
- **THEN** 插件返回 JSON-RPC 成功响应，`result.service_did` 为当前服务 DID，`result.supported_profiles` 包含 `anp.core.binding.v1`，`result.supported_security_profiles` 包含 `transport-protected`

#### Scenario: 能力响应包含限制信息
- **WHEN** 插件返回 `anp.get_capabilities` 成功响应
- **THEN** `result.limits.max_request_bytes` 使用 decimal string 表示当前 HTTP 请求体限制

#### Scenario: 能力响应包含支持内容类型
- **WHEN** 插件返回 `anp.get_capabilities` 成功响应
- **THEN** `result.supported_content_types` 至少包含 `text/plain` 和 `application/json`

### Requirement: Core Binding 参数 envelope
插件 SHALL 支持 ANP Core Binding v1 的 `params.meta/body` envelope，并在支持的方法中从 `params.body` 读取业务参数。

#### Scenario: chat 使用 body.message
- **WHEN** 调用方发送 `chat` 请求，且 `params.meta.profile` 为 `anp.core.binding.v1`，`params.meta.security_profile` 为 `transport-protected`，`params.body.message` 为文本
- **THEN** 插件将 `params.body.message` 作为 Hermes 消息文本处理

#### Scenario: legacy message 继续可用
- **WHEN** 调用方发送当前 legacy `chat` 请求，且 `params.message` 为文本
- **THEN** 插件继续将 `params.message` 作为 Hermes 消息文本处理

#### Scenario: body message 优先
- **WHEN** `chat` 请求同时包含 `params.body.message` 和 `params.message`
- **THEN** 插件优先使用 `params.body.message`

### Requirement: Core Binding profile 校验
插件 SHALL 对 Core Binding envelope 中的 `meta.profile` 与 `meta.security_profile` 执行最小校验，并对不支持的值返回机器可读 JSON-RPC error。

#### Scenario: 不支持的 profile
- **WHEN** 请求包含 Core Binding envelope，且 `params.meta.profile` 不是 `anp.core.binding.v1`
- **THEN** 插件返回 JSON-RPC error，`error.code` 为 `1001`，`error.data.anp_code` 为 `anp.unsupported_profile`

#### Scenario: 不支持的 security profile
- **WHEN** 请求包含 Core Binding envelope，且 `params.meta.security_profile` 不是 `transport-protected`
- **THEN** 插件返回 JSON-RPC error，`error.code` 为 `1002`，`error.data.anp_code` 为 `anp.unsupported_security_profile`

#### Scenario: 无效 params envelope
- **WHEN** 请求包含 Core Binding envelope，但 `params.meta` 或 `params.body` 不是对象
- **THEN** 插件返回 JSON-RPC error，`error.code` 为 `1003`，`error.data.anp_code` 为 `anp.invalid_params_shape`
