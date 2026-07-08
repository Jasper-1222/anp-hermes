## ADDED Requirements

### Requirement: Authentication-Info 测试覆盖
插件测试体系 SHALL 对成功认证响应头行为提供回归测试，确保只在允许场景透传 `Authentication-Info`。

#### Scenario: 成功头透传测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `/agent/rpc` 成功 JSON-RPC 响应会附带 verifier 生成的非空 `Authentication-Info` 头

#### Scenario: 空头和未允许头过滤测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖无 `Authentication-Info` 时不返回空头，且 verifier 返回的 `Authorization` 或其他内部响应头不会被透传