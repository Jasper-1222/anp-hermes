## Why

前十个 OpenSpec 变更已经完成并归档，项目从“逐项补齐能力”进入“社区参考实现候选”阶段。继续加新功能前，需要先做一次收尾审计，确保文档、main specs、测试说明、路线图和实际实现保持一致，避免把过期分析继续当作下一步依据。

## What Changes

- 更新 `docs/anp-hermes-current-implementation-analysis.md`，把已经完成的问题和建议从待办口吻改为当前能力与剩余风险。
- 更新 `docs/anp-hermes-openspec-roadmap.md`，标记前十个变更已完成，并整理下一阶段 backlog。
- 复核并修正 README、插件 README、CLAUDE.md、main specs 与执行状态文档之间的事实不一致。
- 建立社区就绪检查清单：OpenSpec 全量校验、普通测试、coverage、ruff/black、Echo E2E，真实 LLM E2E 作为有凭据时的可选验证。
- 产出下一阶段建议事项，包括生产部署指南、ANP SDK resolver injection 上游协作、Bearer token 后续请求完整验收、限流/审计持久化和社区示例客户端。
- 不新增运行时代码能力，不改变 ANP 对外 API，不扩大 tool RPC 默认暴露范围。

## Capabilities

### New Capabilities

- `anp-community-readiness`: 定义 ANP Hermes 参考实现进入社区贡献候选状态前的文档一致性、验证矩阵、路线图收口和下一阶段 backlog 要求。

### Modified Capabilities

- `anp-platform-adapter`: 修正运行时能力声明要求，明确 Hermes tools 方法不是“尚未实现”，而是仅在 tool RPC 显式启用且工具通过策略校验时才可声明。

## Impact

- 影响文档：`docs/anp-hermes-current-implementation-analysis.md`、`docs/anp-hermes-openspec-roadmap.md`、`docs/anp-hermes-openspec-execution-state.md`、根 `README.md`、插件 `plugins/anp-agent/README.md`、`CLAUDE.md`。
- 影响 OpenSpec：新增 `anp-community-readiness` capability spec，用于记录社区就绪检查契约。
- 影响验证流程：需要运行 OpenSpec 全量校验、插件普通测试、coverage、ruff/black、Echo E2E；真实 LLM E2E 若缺少 provider/API key 则记录为可选未执行项。
- 不影响运行时代码、JSON-RPC 方法、DID WBA 认证、tool RPC 授权策略或插件安装结构。
