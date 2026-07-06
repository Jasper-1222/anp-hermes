# anp-platform-adapter Specification (Delta)

## Purpose

对现有 `anp-platform-adapter` 能力进行增量更新，使其认证失败响应契约与 `anp-auth-error-classification` 能力保持一致。

## MODIFIED Requirements

### Requirement: 通过 Hermes 插件机制自注册
插件 SHALL 继承 `BasePlatformAdapter` 并通过 `ctx.register_platform()` 在 Hermes `platform_registry` 中注册一个名为 `anp` 的平台，无需修改 Hermes 核心代码。

#### Scenario: 注册入口
- **WHEN** Hermes 加载 `~/.hermes/plugins/anp-agent/` 目录下的插件
- **THEN** 插件的 `register(ctx)` 函数被调用，并注册 `anp` 平台及其工厂函数

## ADDED Requirements

### Requirement: JSON-RPC 错误响应契约
当 `/agent/rpc` 认证失败时，适配器 SHALL 返回 `plugins/anp-agent/auth.py` 中 `AuthenticationError` 所携带的 JSON-RPC 错误码与消息，并附带安全的 HTTP 响应头。

#### Scenario: 缺少签名返回 -32003
- **WHEN** 调用方未提供 `Signature` / `Signature-Input` 头
- **THEN** HTTP 响应状态码为 401，JSON-RPC `error.code` 为 `-32003`，`error.message` 为 `缺少认证头`

#### Scenario: DID 文档解析失败返回 -32002
- **WHEN** 调用方 DID 文档无法解析（超时、网络错误、默认 HTTPS 解析失败）
- **THEN** HTTP 响应状态码为 401，JSON-RPC `error.code` 为 `-32002`，`error.message` 为 `DID 文档无法解析`

#### Scenario: 内部认证错误返回 -32006
- **WHEN** 认证过程中出现未预期内部异常
- **THEN** HTTP 响应状态码为 500，JSON-RPC `error.code` 为 `-32006`，`error.message` 为 `认证服务内部错误`

### Requirement: Challenge 头转发
适配器 SHALL 在认证失败响应中转发来自 `DidWbaVerifierError` 的 `WWW-Authenticate` 和 `Accept-Signature` 头（如果存在）。

#### Scenario: 401 响应携带 challenge 头
- **WHEN** verifier 返回 401 并携带 `WWW-Authenticate` 头
- **THEN** `/agent/rpc` 的 401 HTTP 响应包含同名头且值不变

