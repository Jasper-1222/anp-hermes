## ADDED Requirements

### Requirement: 社区就绪状态收口
项目 SHALL 在前十个 OpenSpec 变更完成后，将执行状态文档更新为社区就绪收尾状态，并准确标记 `expose-hermes-tools` 已完成、已同步、已归档。执行 `review-community-readiness` 期间，该变更 SHALL 是唯一 active change；归档后 active change SHALL 恢复为无。

#### Scenario: 执行期间状态反映当前 active change
- **WHEN** 开发者在执行本变更期间阅读 `docs/anp-hermes-openspec-execution-state.md`
- **THEN** 文档声明当前 active change 为 `review-community-readiness`
- **AND** 不再把 `expose-hermes-tools` 描述为 apply 中或待验证归档

#### Scenario: 归档后状态反映无 active change
- **WHEN** `review-community-readiness` 已归档
- **THEN** `openspec list --json` 中 active changes 为空
- **AND** 执行状态文档不再建议进入已经完成的 `expose-hermes-tools`

#### Scenario: 已完成变更被准确记录
- **WHEN** 开发者阅读已完成列表
- **THEN** 前十个变更均被标记为完成
- **AND** `expose-hermes-tools` 的完成内容包含 tool RPC 默认关闭、allowlist/denylist、caller DID 授权、OpenRPC/capabilities/discovery 集成、RPC route 与归档位置

### Requirement: 文档事实一致性审计
项目 SHALL 对面向开发者和社区贡献者的主要文档执行事实一致性审计，确保它们不再引用已过期的 active change、旧模块路径或已完成待办。

#### Scenario: 主要文档一致
- **WHEN** 开发者阅读根 README、插件 README、CLAUDE.md、执行状态文档、路线图和当前实现分析报告
- **THEN** 这些文档对当前能力、插件包路径、默认 data dir、resolver override 边界、tool RPC 默认关闭和测试命令的描述一致

#### Scenario: 旧待办被收口
- **WHEN** 文档包含早期 P0/P1/P2 建议或 Top 10 优先建议
- **THEN** 已完成事项 SHALL 被标记为完成或改写为当前能力
- **AND** 未完成事项 SHALL 被移动到下一阶段 backlog，而不是继续混在已完成路线图中

### Requirement: 社区就绪验证矩阵
项目 SHALL 记录并执行社区就绪所需的本地验证矩阵，区分必须通过的本地检查和依赖外部凭据的条件检查。

#### Scenario: 必须验证通过
- **WHEN** 执行社区就绪收尾审计
- **THEN** 必须运行并通过 OpenSpec 全量校验、插件普通测试、coverage、ruff/black 和 Echo E2E

#### Scenario: 条件验证记录
- **WHEN** 真实 LLM E2E 缺少 provider 配置或 API key
- **THEN** 文档 SHALL 将真实 LLM E2E 记录为条件未执行或按预期 skip
- **AND** 不得把未执行的真实 LLM E2E 描述为已通过

### Requirement: 下一阶段 backlog
项目 SHALL 在完成社区就绪收尾后整理下一阶段 backlog，仅保留真实未完成且可独立 OpenSpec 化的主题。

#### Scenario: backlog 聚焦后续工作
- **WHEN** 开发者查看下一步建议
- **THEN** 文档列出生产部署指南、ANP SDK resolver injection 上游协作、Bearer token 后续请求完整验收、限流/审计持久化和社区示例客户端等候选主题
- **AND** 不再建议进入已经完成并归档的 `expose-hermes-tools`

#### Scenario: 推荐下一步操作
- **WHEN** 开发者希望继续推进
- **THEN** 文档 SHALL 建议先完成 `review-community-readiness` 收尾审计，再按 backlog 创建后续 OpenSpec 变更或进入 PR/发布流程
