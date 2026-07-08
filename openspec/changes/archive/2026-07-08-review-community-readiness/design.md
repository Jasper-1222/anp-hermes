## Context

项目已按长期路线图连续完成并归档十个 OpenSpec 变更；创建本变更前没有 active change，执行本变更期间 `review-community-readiness` 是唯一 active change。运行时代码已经具备 DID WBA 认证、JSON-RPC bridge、Core Binding、主动发现、包化插件、生产 resolver 边界、测试体系加固以及默认关闭的 Hermes tool RPC。

剩余风险不再主要是单个功能缺失，而是“已完成状态是否被准确记录、是否足够适合作为社区参考实现提交”。当前 `docs/anp-hermes-current-implementation-analysis.md` 和 `docs/anp-hermes-openspec-roadmap.md` 仍保留早期 P0/P1/P2 待办口吻，容易让后续开发者误以为已完成事项仍未实现。

## Goals / Non-Goals

**Goals:**

- 将项目文档从“执行中路线图”收口为“社区参考实现候选”的当前状态说明。
- 复核 README、插件 README、CLAUDE.md、执行状态文档、路线图和 main specs 的事实一致性。
- 明确社区就绪验证矩阵，让后续 PR 或发布前检查有稳定入口。
- 整理下一阶段 backlog，只保留真实未完成、值得后续独立 OpenSpec 化的事项。

**Non-Goals:**

- 不新增运行时代码能力。
- 不改变 DID WBA、JSON-RPC、discovery、Core Binding 或 tool RPC 的行为契约。
- 不扩大 tool RPC 默认暴露范围。
- 不在本变更中实现生产部署、限流、持久化审计或 AP2/E2EE。
- 不重写项目定位，只做事实更新和收尾审计。

## Decisions

### Decision 1: 以文档事实收口为主，不改运行时代码

本变更的核心是让文档、规格和验证记录反映已完成事实。运行时代码已经通过前十个变更分别验证，继续把代码改动混入本变更会降低审计清晰度。

替代方案是顺手实现下一阶段功能，例如限流或持久化审计。该方案会把“收尾审计”和“新能力设计”混在一起，导致归档后仍难判断社区就绪状态，因此不采用。

### Decision 2: 新增 `anp-community-readiness` capability spec

社区就绪不是单个 API 行为，而是一组可验证的发布前约束：文档一致性、验证矩阵、backlog 整理和 no active changes 状态。新增独立 capability 可以让这些要求在 OpenSpec 中被追踪，而不污染运行时能力 specs。

替代方案是不新增 spec，只更新文档。该方案缺少验收契约，后续 archive 时无法判断“收尾审计”是否完成，因此不采用。

### Decision 3: 将真实 LLM E2E 标记为条件验证

真实 LLM E2E 依赖本机 Hermes provider 配置和对应 API key。社区就绪矩阵应要求普通测试、coverage、ruff/black、Echo E2E 和 OpenSpec 全量校验必须通过；真实 LLM E2E 在缺少 provider/API key 时记录为条件未执行，而不是阻塞本地收尾。

替代方案是强制真实 LLM E2E 必跑。该方案会让无凭据环境无法完成收尾审计，不适合作为通用社区参考实现检查，因此不采用。

### Decision 4: 下一阶段 backlog 只记录独立可执行主题

下一阶段事项应写成可独立 OpenSpec 化的主题，例如生产部署指南、ANP SDK resolver injection、Bearer token 后续请求完整验收、限流/审计持久化和社区示例客户端。已经完成的前十项不再保留为待办。

替代方案是继续维护原 Top 10 列表并逐条标注已完成。该方案历史信息多但行动价值低，容易让新会话误读优先级，因此只在执行状态中保留完成记录，在路线图中转为下一阶段 backlog。

## Risks / Trade-offs

- **过度改写历史分析** → 只更新明显过期的事实和待办，不重写项目定位或删除有参考价值的分析背景。
- **文档遗漏某个已完成能力** → 用 main specs、README、插件 README、CLAUDE.md 和 archived changes 交叉检查。
- **验证矩阵耗时增加** → 将必须验证与条件验证分层；真实 LLM E2E 只在有凭据时执行。
- **backlog 过宽** → 只列出后续可独立成变更的主题，不在本变更展开实现细节。

## Migration Plan

1. 更新执行状态文档，确认前十个变更已完成归档，并记录当前 active change 为 `review-community-readiness`；本变更归档后 active change 应恢复为无。
2. 更新当前实现分析报告，把已完成 P0/P1/P2 项从风险/建议口吻改为当前能力和剩余风险。
3. 更新路线图，标记前十个变更完成，新增下一阶段 backlog。
4. 复核 README、插件 README、CLAUDE.md 与 main specs 的事实一致性。
5. 运行社区就绪验证矩阵并记录结果。
6. 在 apply 完成后，通过 `/opsx:sync review-community-readiness` 同步 `anp-community-readiness` main spec，再通过 `/opsx:archive review-community-readiness` 归档本变更。

回滚策略：本变更主要修改文档和 OpenSpec 规划文件。若发现收口判断过早，可恢复相关文档段落或新建后续 change 修正 backlog，不影响运行时代码。

## Open Questions

- 是否将真实 LLM E2E 结果作为 PR 合并前硬门禁，还是继续保持“有凭据时执行”的条件验证？建议本变更先保持条件验证。
- 下一阶段是否优先做生产部署指南，还是优先做 ANP SDK resolver injection 上游协作？建议由收尾审计后的 backlog 决定。
