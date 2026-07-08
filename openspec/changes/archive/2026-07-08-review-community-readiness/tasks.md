## 1. 当前状态收口

- [x] 1.1 更新 `docs/anp-hermes-openspec-execution-state.md`，确认前十个变更已归档，并记录当前 active change 为 `review-community-readiness`。
- [x] 1.2 确认 `expose-hermes-tools` 在执行状态文档中已标记为实现、验证、同步和归档完成。
- [x] 1.3 运行 `openspec list --json`，确认 active changes 与文档状态一致。

## 2. 分析报告与路线图更新

- [x] 2.1 更新 `docs/anp-hermes-current-implementation-analysis.md`，将已完成的 P0/P1/P2 问题改为当前能力与剩余风险。
- [x] 2.2 更新 `docs/anp-hermes-openspec-roadmap.md`，标记前十个变更已完成，并移除已完成事项的待办口吻。
- [x] 2.3 在路线图中新增下一阶段 backlog，聚焦生产部署指南、ANP SDK resolver injection、Bearer token 后续请求完整验收、限流/审计持久化和社区示例客户端。

## 3. 主要文档一致性审计

- [x] 3.1 复核根 `README.md`，确认当前能力、安装方式、tool RPC 默认关闭、安全边界和测试命令与实现一致。
- [x] 3.2 复核 `plugins/anp-agent/README.md`，确认配置示例、包化结构、resolver override、tool RPC 和 E2E 说明与实现一致。
- [x] 3.3 复核 `CLAUDE.md`，确认项目目标、开发命令、OpenSpec 状态、安装说明和安全约束与当前状态一致。
- [x] 3.4 复核 main specs，确认没有继续把已完成能力列为未实现，也没有声明未支持的 AP2、E2EE、Direct/Group 或默认开启 tool RPC。

## 4. 社区就绪验证矩阵

- [x] 4.1 运行并通过 `openspec validate --all`。
- [x] 4.2 在 `plugins/anp-agent` 下运行并通过 `python3 -m pytest tests/ -q`。
- [x] 4.3 在 `plugins/anp-agent` 下运行并通过 `python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q`。
- [x] 4.4 在 `plugins/anp-agent` 下运行并通过 `ruff check . && black --check .`。
- [x] 4.5 在 `plugins/anp-agent` 下运行并通过 `python3 -m pytest tests/e2e/test_echo.py -v --run-e2e`。
- [x] 4.6 如有真实 LLM provider 与 API key，运行 `python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e`；否则记录为条件未执行。

## 5. OpenSpec 校验与交接准备

- [x] 5.1 运行并通过 `openspec validate review-community-readiness --strict` 或等效 change 校验。
- [x] 5.2 运行并记录归档前一致性检查，确认任务、规格覆盖和文档状态没有自指未完成项。
- [x] 5.3 确认 `anp-community-readiness` delta spec 已准备好在 apply 完成后同步到 main specs。
- [x] 5.4 在完成摘要中明确下一步应运行 `/opsx:sync review-community-readiness` 与 `/opsx:archive review-community-readiness`。
