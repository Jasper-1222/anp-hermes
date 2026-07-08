## MODIFIED Requirements

### Requirement: 协议关键路径回归基线
`anp-agent` 测试体系 SHALL 覆盖当前已实现的协议关键路径，防止后续重构破坏 JSON-RPC 错误语义、成功认证响应头、身份持久化、公开发现、能力文档契约和 DID resolver 生产边界。

#### Scenario: JSON-RPC 错误语义有回归测试
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 invalid request、unknown method、bridge timeout、cancelled pending、handler exception 和 pending capacity exhausted 的 JSON-RPC error 响应

#### Scenario: 成功认证响应头有回归测试
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖成功认证时只透传允许的 `Authentication-Info` 响应头，且无认证响应头时不返回空头

#### Scenario: 身份持久化边界有回归测试
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖默认数据目录、显式数据目录、私钥 `0o600` 权限、已有身份加载和损坏身份备份

#### Scenario: 公开发现与能力文档有回归测试
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json` 和 `anp.get_capabilities` 的当前公开契约

#### Scenario: DID resolver 生产边界有回归测试
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 loopback resolver override 成功路径、非 loopback override 拒绝、HTTPS override 的 TLS 校验参数、timeout 边界、多实例 override 冲突和 resolver 错误安全分类

#### Scenario: E2E resolver override 被隔离
- **WHEN** 运行 Echo E2E fixture 测试
- **THEN** `ANP_DID_RESOLVER_BASE_URL` 仅注入临时测试环境
- **AND** 不依赖或修改用户真实 `~/.hermes/config.yaml`