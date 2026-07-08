## MODIFIED Requirements

### Requirement: 通过 Hermes 插件机制自注册
插件 SHALL 继承 `BasePlatformAdapter` 并通过 `ctx.register_platform()` 在 Hermes `platform_registry` 中注册一个名为 `anp` 的平台，无需修改 Hermes 核心代码。插件在包化后 SHALL 保持根目录 `__init__.py:register` 入口可用，并通过 Hermes package 上下文中的相对导入 `.anp_agent.*` 加载业务模块，不得依赖将插件根目录插入全局 `sys.path` 来解析 `adapter`、`config` 等通用顶层模块名。

#### Scenario: 注册入口
- **WHEN** Hermes 加载 `~/.hermes/plugins/anp-agent/` 目录下的插件
- **THEN** 插件的 `register(ctx)` 函数被调用，并注册 `anp` 平台及其工厂函数

#### Scenario: 包化入口注册
- **WHEN** Hermes 加载包化后的 `anp-agent` 插件根目录
- **THEN** 根目录 `__init__.py:register` 使用相对导入 `.anp_agent.adapter.ANPAdapter` 注册 `anp` 平台，且不需要业务模块作为顶层 `adapter` 模块存在

#### Scenario: 不污染全局 import 路径
- **WHEN** 插件 entrypoint 被导入或 `register(ctx)` 被调用
- **THEN** 插件不会将自身根目录插入 `sys.path` 以解析业务模块
