## MODIFIED Requirements

### Requirement: 社区就绪状态收口
项目 SHALL 准确记录截至 `close-demo-readiness` 之前的 17 个 OpenSpec 变更均已归档。执行 `close-demo-readiness` 期间，该变更 SHALL 是唯一 active change；归档后 active changes SHALL 恢复为空，并记录技术 Demo P0/P1 已完成。

#### Scenario: 执行期间状态准确
- **WHEN** 开发者在本变更执行期间阅读执行状态文档
- **THEN** 文档声明唯一 active change 为 `close-demo-readiness`
- **AND** 文档不再把 `review-community-readiness` 描述为执行中

#### Scenario: 归档后状态准确
- **WHEN** `close-demo-readiness` 已归档
- **THEN** `openspec list --json` 中 active changes 为空
- **AND** 文档记录客户端 skill、双发布包、ANP SDK 0.8.9 和 Demo 收口均已完成

### Requirement: 文档事实一致性审计
项目 SHALL 对根 README、插件 README、CLAUDE.md、执行状态、路线图、实现分析和 main specs 执行事实一致性审计，确保它们对技术 Demo 定位、当前能力、测试命令、发布资产、LICENSE、默认审计 sink 和 OpenSpec 状态的描述一致。

#### Scenario: 主要文档一致
- **WHEN** 开发者阅读主要文档
- **THEN** 文档均说明项目是 ANP × Hermes 技术验证 Demo
- **AND** 文档不声称当前已经创建 GitHub Release
- **AND** 文档不把默认未配置的 audit callback 描述为已持久化审计记录

#### Scenario: 当前能力被准确记录
- **WHEN** 开发者查看仓库结构和能力清单
- **THEN** 文档包含 Hermes plugin、ANP client skill、双发布包和 ANP SDK 0.8.9
- **AND** 不再建议先完成已经归档的 `review-community-readiness`

### Requirement: 社区就绪验证矩阵
项目 SHALL 执行技术 Demo 的最低本地验证矩阵，覆盖 OpenSpec、根级测试、客户端测试、插件普通测试、插件覆盖率、Ruff、Black、本地无凭据 E2E 和发布包构建。

#### Scenario: 必须验证通过
- **WHEN** 执行 Demo 收口
- **THEN** OpenSpec、根级、客户端、插件、覆盖率、Ruff、Black 和发布包构建全部通过
- **AND** 无凭据本地 E2E 通过，真实 LLM E2E 可记录为条件未执行

#### Scenario: 不伪造外部验证
- **WHEN** 本轮未创建 GitHub Release 或未重新运行真实 LLM E2E
- **THEN** 文档不得把这些外部或条件动作描述为本轮已完成

### Requirement: 下一阶段 backlog
项目 SHALL 将生产部署、Bearer 扩展、限流、持久化审计、resolver 上游改造、跨机器 DID、AP2 和 E2EE 明确保留为当前技术 Demo 范围外的可选后续主题，不得在 `close-demo-readiness` 中实施。

#### Scenario: P2 不进入本轮
- **WHEN** 开发者检查本变更的代码、文档和任务
- **THEN** 本变更只包含 Demo P0/P1 收口
- **AND** 不包含任何 P2 或生产级能力实现

#### Scenario: 推荐下一步操作
- **WHEN** `close-demo-readiness` 归档完成
- **THEN** 项目可以保留当前技术 Demo 状态供社区体验
- **AND** 不要求继续创建生产化 OpenSpec change 才能完成本轮
