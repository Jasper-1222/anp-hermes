## ADDED Requirements

### Requirement: 技术 Demo 双发布资产与许可证
发布脚本 SHALL 为 plugin 与 client skill 分别生成版本化资产和稳定别名。稳定别名 MUST 与对应版本化资产字节一致，两个逻辑发布包 MUST 在归档根目录包含仓库 MIT `LICENSE`。

#### Scenario: 一次打包生成四个资产
- **WHEN** 开发者以版本 `0.1.0` 运行发布脚本
- **THEN** 输出目录包含 `anp-agent-plugin-0.1.0.zip` 和 `anp-agent.zip`
- **AND** 输出目录包含 `anp-client-skill-0.1.0.zip` 和 `anp-client.zip`
- **AND** 两个稳定别名分别与对应版本化资产字节一致

#### Scenario: 发布包包含许可证
- **WHEN** 开发者检查 plugin 或 client skill zip
- **THEN** 归档根目录包含 `LICENSE`
- **AND** `LICENSE` 内容来自仓库根 MIT 许可证文件

#### Scenario: 干净 clone 可执行包化测试
- **WHEN** 在没有预生成 `*.zip` 的干净 clone 中运行普通测试
- **THEN** 测试在临时目录调用发布脚本生成待检查归档
- **AND** 测试不要求 `plugins/anp-agent/anp-agent.zip` 预先存在
