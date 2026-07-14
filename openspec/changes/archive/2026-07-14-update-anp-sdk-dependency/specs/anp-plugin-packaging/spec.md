## MODIFIED Requirements

### Requirement: Python 打包配置匹配包化结构
插件 SHALL 在 `pyproject.toml` 中声明可安装的 `anp_agent` 包，并让 editable install、测试、lint、format 与 coverage 命令针对包化结构运行。插件 SHALL 声明 ANP Python SDK 依赖为 `anp>=0.8.9,<0.9.0`，测试 extras 中的 `anp[api]` 依赖 SHALL 使用相同版本边界。

#### Scenario: editable install 后包可导入
- **WHEN** 开发者在 `plugins/anp-agent` 下运行 `python3 -m pip install -e ".[test,dev]"`
- **THEN** Python 环境可导入 `anp_agent` 包及其运行时模块
- **AND** 安装解析出的 ANP SDK 版本满足 `anp>=0.8.9,<0.9.0`

#### Scenario: coverage 使用包名口径
- **WHEN** 开发者运行 coverage 测试
- **THEN** coverage source 或命令以 `anp_agent` 为运行时代码统计边界，并继续满足覆盖率阈值

#### Scenario: 插件依赖边界与最新上游基线一致
- **WHEN** 开发者检查 `plugins/anp-agent/pyproject.toml`
- **THEN** `project.dependencies` 中的 ANP SDK 依赖为 `anp>=0.8.9,<0.9.0`
- **AND** `project.optional-dependencies.test` 中的 `anp[api]` 依赖为 `anp[api]>=0.8.9,<0.9.0`
