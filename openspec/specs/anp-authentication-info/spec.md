# anp-authentication-info Specification

## Purpose

定义 `anp-agent` 插件在 DID WBA HTTP Message Signatures 认证成功后，向调用方返回安全认证成功响应头的契约。

## Requirements

### Requirement: 成功认证返回 Authentication-Info
插件 SHALL 在 DID WBA HTTP Message Signatures 认证成功且 verifier 生成 `Authentication-Info` 时，将该响应头返回给调用方。

#### Scenario: 成功认证响应携带 Authentication-Info
- **WHEN** `/agent/rpc` 请求通过 DID WBA HTTP Message Signatures 认证，且认证器生成 `Authentication-Info` 响应头
- **THEN** HTTP 200 JSON-RPC 成功响应包含同名 `Authentication-Info` 头

#### Scenario: 无认证响应头时不返回空头
- **WHEN** `/agent/rpc` 请求认证成功但认证器未生成 `Authentication-Info` 响应头
- **THEN** HTTP 响应不包含空的 `Authentication-Info` 头

### Requirement: 成功认证响应头过滤
插件 SHALL 只转发明确允许的成功认证响应头，不得将 verifier 返回的任意响应头透传给调用方。

#### Scenario: 仅转发 Authentication-Info
- **WHEN** verifier 成功认证结果包含 `Authentication-Info`、`Authorization` 与其他内部响应头
- **THEN** `/agent/rpc` 成功响应只包含允许的 `Authentication-Info` 头，不包含响应 `Authorization` 或内部头

### Requirement: Authentication-Info 测试覆盖
插件测试体系 SHALL 对成功认证响应头行为提供回归测试，确保只在允许场景透传 `Authentication-Info`。

#### Scenario: 成功头透传测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `/agent/rpc` 成功 JSON-RPC 响应会附带 verifier 生成的非空 `Authentication-Info` 头

#### Scenario: 空头和未允许头过滤测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖无 `Authentication-Info` 时不返回空头，且 verifier 返回的 `Authorization` 或其他内部响应头不会被透传
