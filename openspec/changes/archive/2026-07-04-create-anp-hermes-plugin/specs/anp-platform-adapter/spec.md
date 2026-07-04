## ADDED Requirements

### Requirement: 通过 Hermes 插件机制自注册
插件 SHALL 继承 `BasePlatformAdapter` 并通过 `ctx.register_platform()` 在 Hermes `platform_registry` 中注册一个名为 `anp` 的平台，无需修改 Hermes 核心代码。

#### Scenario: 注册入口
- **WHEN** Hermes 加载 `~/.hermes/plugins/anp-agent/` 目录下的插件
- **THEN** 插件的 `register(ctx)` 函数被调用，并注册 `anp` 平台及其工厂函数

### Requirement: 生命周期管理
适配器 SHALL 实现 `connect()` 和 `disconnect()`，管理内部 HTTP 服务器的启动与停止。

#### Scenario: 连接成功
- **WHEN** `connect()` 被调用且 DID 身份已就绪
- **THEN** 启动 aiohttp 服务器监听配置的 host 和 port，并调用 `_mark_connected()`

#### Scenario: 断开连接
- **WHEN** `disconnect()` 被调用
- **THEN** 停止 aiohttp 服务器，取消后台任务，并调用 `_mark_disconnected()`

### Requirement: 配置来源
适配器 SHALL 同时支持 `config.yaml` 的 `extra` 字段和环境变量，环境变量优先级高于配置文件。

#### Scenario: 环境变量覆盖
- **WHEN** 同时设置了 `ANP_HOST` / `ANP_PORT` 环境变量和 `config.yaml` 中的 `host` / `port`
- **THEN** 使用环境变量的值

### Requirement: send 桥接
适配器 SHALL 实现 `send(chat_id, content, ...)`，当 `chat_id` 以 `anp:` 前缀标识某次 JSON-RPC 调用时，将该调用标记为已完成并返回结果。

#### Scenario: 回复 ANP 调用
- **WHEN** Hermes 处理完 ANP 调用并通过 `send()` 发送回复
- **THEN** 对应的 JSON-RPC 响应被返回给调用方
