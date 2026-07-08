# anp-test-harness Specification

## Purpose

定义 `anp-agent` 插件测试体系的隔离性、覆盖率、E2E gating 与协议关键路径回归测试要求，确保后续重构和能力扩展有稳定、可重复的质量基线。

## Requirements

### Requirement: 覆盖率统计边界
`anp-agent` 测试体系 SHALL 将覆盖率统计限定在插件运行时代码范围内，并显式排除测试代码、E2E helper、Python 缓存和运行态身份/密钥文件。

#### Scenario: coverage source 指向运行时代码
- **WHEN** 开发者在 `plugins/anp-agent` 下运行覆盖率测试
- **THEN** coverage 统计的 source 为当前插件运行时代码，而不是整个测试树

#### Scenario: coverage omit 排除非运行时代码
- **WHEN** coverage 生成报告
- **THEN** 报告不把 `tests/`、`tests/e2e/`、`tests/helpers/`、`__pycache__/` 或运行态 DID/PEM 文件计入覆盖率门槛

### Requirement: 测试命令文档
`anp-agent` 文档 SHALL 明确普通测试、覆盖率测试、确定性 Echo E2E 和真实 LLM E2E 的运行命令与前置条件。

#### Scenario: 文档区分 Echo E2E 与 LLM E2E
- **WHEN** 开发者阅读测试文档
- **THEN** 文档说明 Echo E2E 使用 mock LLM 且无需真实 API key，LLM E2E 需要 `--run-e2e --run-slow-e2e` 和 provider 凭据

#### Scenario: 文档说明覆盖率门槛
- **WHEN** 开发者阅读测试文档
- **THEN** 文档包含覆盖率检查命令并说明覆盖率要求不低于 85%

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
