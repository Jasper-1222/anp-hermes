## MODIFIED Requirements

### Requirement: 社区就绪状态收口
项目 SHALL 准确记录截至 `close-demo-readiness` 之前的 17 个 OpenSpec 变更均已完成、同步并归档，其中 `expose-hermes-tools` 的完成证据 SHALL 包含 tool RPC 默认关闭、allowlist/denylist、caller DID 授权、OpenRPC/capabilities/discovery 集成、RPC route 与归档位置。执行 `close-demo-readiness` 期间，该变更 SHALL 是唯一 active change；归档后 active changes SHALL 恢复为空，并记录技术 Demo P0/P1 已完成。

#### Scenario: 执行期间状态准确
- **WHEN** 开发者在本变更执行期间阅读 `docs/anp-hermes-openspec-execution-state.md`
- **THEN** 文档声明唯一 active change 为 `close-demo-readiness`
- **AND** 文档不再把 `review-community-readiness` 或其他已归档变更描述为执行中

#### Scenario: 归档后状态准确
- **WHEN** `close-demo-readiness` 已归档
- **THEN** `openspec list --json` 中 active changes 为空
- **AND** 文档记录客户端 skill、双发布包、ANP SDK 0.8.9 和 Demo 收口均已完成
- **AND** 文档不再建议进入任何已经完成并归档的 change

#### Scenario: 已完成变更被准确记录
- **WHEN** 开发者阅读已完成变更列表
- **THEN** `close-demo-readiness` 之前的 17 个变更均被标记为完成、同步并归档
- **AND** `expose-hermes-tools` 的完成内容包含 tool RPC 默认关闭、allowlist/denylist、caller DID 授权、OpenRPC/capabilities/discovery 集成、RPC route 与归档证据

### Requirement: 文档事实一致性审计
项目 SHALL 对根 README、插件 README、CLAUDE.md、执行状态、路线图、实现分析和 main specs 执行事实一致性审计，确保它们对 ANP × Hermes 技术验证 Demo 定位、当前能力、插件包路径、默认 data dir、resolver loopback override 边界、tool RPC 默认关闭、测试命令、发布资产、LICENSE、默认审计 sink、OpenSpec 状态和已完成待办的描述一致。

#### Scenario: 主要文档一致
- **WHEN** 开发者阅读根 README、插件 README、CLAUDE.md、执行状态文档、路线图、当前实现分析和 main specs
- **THEN** 文档对当前能力、插件包路径、默认 data dir、resolver loopback override 边界、tool RPC 默认关闭和测试命令的描述一致
- **AND** 文档均将项目定位为 ANP × Hermes 技术验证 Demo
- **AND** 文档不声称当前已经创建 GitHub Release
- **AND** 文档不把默认未配置的 audit callback 描述为已持久化审计记录

#### Scenario: 当前能力被准确记录
- **WHEN** 开发者查看仓库结构和能力清单
- **THEN** 文档包含 Hermes plugin、ANP client skill、双发布包和 ANP SDK 0.8.9
- **AND** 不再建议先完成已经归档的 `review-community-readiness`

#### Scenario: 旧待办被收口
- **WHEN** 文档包含早期 P0/P1/P2 建议或 Top 10 优先建议
- **THEN** 已完成事项 SHALL 被标记为完成或改写为当前能力
- **AND** 真实未完成事项 SHALL 被移动到下一阶段 backlog，而不是继续混在已完成路线图中

### Requirement: 社区就绪验证矩阵
项目 SHALL 记录并执行技术 Demo 的最低本地验证矩阵，覆盖 OpenSpec 全量校验、根级测试、客户端测试、插件普通测试、插件 `>=85%` 覆盖率、Ruff、Black、Echo E2E、本地无凭据 E2E 和四个发布资产构建，并区分必须通过的本地检查与依赖外部凭据的条件检查。

#### Scenario: 必须验证通过
- **WHEN** 执行 Demo 收口
- **THEN** OpenSpec 全量校验、根级测试、客户端测试、插件普通测试和插件 `>=85%` 覆盖率门禁全部通过
- **AND** 根级、客户端和插件 Ruff/Black 全部通过
- **AND** Echo E2E 与本地无凭据 E2E 通过
- **AND** 版本化 plugin/client zip 与两个稳定别名共四个发布资产构建通过

#### Scenario: 条件验证记录
- **WHEN** 真实 LLM E2E 缺少 provider 配置或 API key
- **THEN** 文档 SHALL 将真实 LLM E2E 记录为条件未执行或按预期 skip
- **AND** 不得把未执行的真实 LLM E2E 描述为已通过

#### Scenario: 不伪造外部验证
- **WHEN** 本轮未创建 GitHub Release 或未重新运行真实 LLM E2E
- **THEN** 文档不得把这些外部或条件动作描述为本轮已完成

### Requirement: 下一阶段 backlog
项目 SHALL 在完成技术 Demo P0/P1 收口后，仅保留真实未完成且可独立 OpenSpec 化的下一阶段主题，包括生产部署指南、Bearer token 后续请求完整验收、ANP SDK resolver injection 上游协作、限流与持久化审计以及社区示例客户端；这些主题与跨机器 DID、AP2、E2EE 等生产化或 P2 能力均不得在 `close-demo-readiness` 中实施。

#### Scenario: backlog 聚焦后续工作
- **WHEN** 开发者查看下一步建议
- **THEN** 文档仅列出真实未完成且可独立 OpenSpec 化的候选主题
- **AND** 候选可包含生产部署指南、Bearer token 后续请求完整验收、ANP SDK resolver injection 上游协作、限流与持久化审计以及社区示例客户端
- **AND** 不再建议进入任何已经完成并归档的 change

#### Scenario: P2 不进入本轮
- **WHEN** 开发者检查本变更的代码、文档和任务
- **THEN** 本变更只包含 Demo P0/P1 收口
- **AND** 不包含任何 P2 或生产级能力实现

#### Scenario: 推荐下一步操作
- **WHEN** `close-demo-readiness` 归档完成
- **THEN** 项目可以保留当前技术 Demo 状态供社区体验，不要求继续生产化才能完成本轮
- **AND** 如需继续推进，可以为真实未完成主题创建新的 OpenSpec change，或进入 PR/发布流程
