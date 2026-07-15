## ADDED Requirements

### Requirement: 技术 Demo 最低 CI 门禁
项目 SHALL 提供 Python 3.12 单版本 GitHub Actions 门禁，并在默认分支 `master` 的 push 与 pull request 上触发。门禁 MUST 覆盖 OpenSpec、根级测试、客户端测试、插件测试、插件覆盖率、Ruff、Black 和发布包构建。

#### Scenario: 默认分支触发 CI
- **WHEN** 提交被 push 到 `master` 或 pull request 以 `master` 为目标分支
- **THEN** CI workflow 被触发
- **AND** workflow 使用 Python 3.12

#### Scenario: CI 覆盖技术 Demo 组件
- **WHEN** CI job 执行
- **THEN** 运行 `openspec validate --all`
- **AND** 运行根级和客户端 pytest
- **AND** 运行根级、客户端和插件 Ruff/Black
- **AND** 构建四个发布资产
- **AND** 运行插件普通测试和 `>=85%` 覆盖率门禁

#### Scenario: 确定性测试不占用固定端口
- **WHEN** 本机已有服务监听默认 ANP 端口
- **THEN** adapter 单元测试仍使用动态端口完成连接与断开验证
- **AND** 测试不要求停止用户服务
