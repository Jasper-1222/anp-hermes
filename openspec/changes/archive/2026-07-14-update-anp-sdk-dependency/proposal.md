## Why

ANP Python SDK 本地最新源码 `/home/peter/agent-network-protocol/anp/pyproject.toml` 已更新到 `0.8.9`，而本项目的依赖声明、README 和历史验证说明仍以 `0.8.8` 为基线。为了后续贡献给 ANP 社区，项目需要把依赖版本信息收敛到当前上游版本，并保留主版本兼容边界。

## What Changes

- 将运行时依赖声明从 `anp>=0.8.8,<0.9.0` 更新为 `anp>=0.8.9,<0.9.0`。
- 更新根 README 中的 ANP SDK 依赖说明，避免社区贡献材料继续引用旧基线。
- 更新客户端 skill 的 `requirements.txt`，确保安装包使用最新 ANP SDK 最低版本。
- 更新插件 `pyproject.toml` 依赖边界，保持 plugin 与 skill 对 ANP SDK 的版本要求一致。
- 更新仍作为当前发布/验证参考的文档中旧版本说明；不改写已归档 OpenSpec 历史记录。
- 不改变运行时逻辑、协议行为、endpoint、安全策略或打包结构。

## Capabilities

### New Capabilities

无。本变更只更新依赖版本信息，不引入新的产品能力。

### Modified Capabilities

- `anp-plugin-packaging`: 插件 Python 打包配置的 ANP SDK 依赖最低版本提升到 `0.8.9`，并保持 `<0.9.0` 上限。
- `anp-client-skill`: skill 安装包依赖说明中的 ANP SDK 最低版本提升到 `0.8.9`，并保持 `<0.9.0` 上限。

## Impact

- 受影响代码/配置：
  - `plugins/anp-agent/pyproject.toml`
  - `clients/anp-client/requirements.txt`
  - 根 README 和当前仍有效的依赖说明文档
  - 可能涉及发布打包测试中对文件内容的固定断言
- 受影响外部依赖：
  - ANP Python SDK 最低版本提升到 `0.8.9`，上限保持 `<0.9.0`
- 验证范围：
  - 插件与客户端依赖声明一致性检查
  - `anp-client` 单元/集成测试
  - 发布打包脚本测试
  - 必要时运行插件核心测试确认 ANP SDK API 兼容性
