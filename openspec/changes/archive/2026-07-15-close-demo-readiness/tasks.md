## 1. 分支与 README 保全

- [x] 1.1 提交 README worktree 中的 README，并保全 README 设计与计划文档。
- [x] 1.2 通过 git merge 集成技术 Demo 收口设计分支和 README 分支，保全 README 与技术 Demo 收口的全部四份设计/计划文档。
- [x] 1.3 从 master 建立统一 `chore/close-demo-readiness` 分支，并确认四份设计/计划文档均已进入分支历史。

## 2. 打包、许可证与干净 clone

- [ ] 2.1 为四个发布资产和 LICENSE 编写失败测试。
- [ ] 2.2 添加根 MIT LICENSE。
- [ ] 2.3 实现版本化资产与稳定别名。
- [ ] 2.4 让插件包化测试在临时目录构建归档。
- [ ] 2.5 移除根级依赖测试对本机上游绝对路径的依赖。

## 3. 最低质量与 CI

- [ ] 3.1 让 adapter 连接测试显式使用动态端口。
- [ ] 3.2 修复已知 Black 和 Ruff 门禁。
- [ ] 3.3 将 CI 改为监听 master 的 Python 3.12 单版本完整门禁。

## 4. 文档与规格事实同步

- [ ] 4.1 更新根 README 与插件 README 的测试、资产和许可证说明。
- [ ] 4.2 更新 CLAUDE.md、执行状态、路线图与实现分析。
- [ ] 4.3 直接更新 main spec，为 `anp-client-skill` 填写正式 Purpose；OpenSpec 1.5.0 delta 不管理 Purpose。
- [ ] 4.4 确认文档不宣称本轮已创建 Release 或重新通过真实 LLM E2E。

## 5. 验证与归档

- [ ] 5.1 运行 OpenSpec、根级、客户端、插件、覆盖率、Ruff、Black、E2E、打包门禁和 `git diff --check`。
- [ ] 5.2 运行干净 clone smoke 验证。
- [ ] 5.3 通过 archive 将 `anp-plugin-packaging`、`anp-test-harness` 和 `anp-community-readiness` 三个 requirement delta 同步到 main specs，并归档 `close-demo-readiness`；`anp-client-skill` Purpose 不经 delta 同步。
- [ ] 5.4 确认 active changes 为空并记录最终验证结果。
