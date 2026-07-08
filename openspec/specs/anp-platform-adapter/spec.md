# anp-platform-adapter Specification

## Purpose

定义 `anp-agent` 插件作为 Hermes 平台适配器的集成契约：通过插件机制注册 `anp` 平台，管理内部 HTTP 服务生命周期，从配置加载运行参数，并通过 `send()` 将 Hermes 回复桥接回对应 JSON-RPC 调用。

## Requirements

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

### Requirement: 生命周期管理
适配器 SHALL 实现 `connect()` 和 `disconnect()`，管理内部 HTTP 服务器的启动与停止。

#### Scenario: 连接成功
- **WHEN** `connect()` 被调用且 DID 身份已就绪
- **THEN** 启动 aiohttp 服务器监听配置的 host 和 port，并调用 `_mark_connected()`

#### Scenario: 断开连接
- **WHEN** `disconnect()` 被调用
- **THEN** 停止 aiohttp 服务器，取消后台任务，并调用 `_mark_disconnected()`

### Requirement: 配置来源
适配器 SHALL 同时支持 `config.yaml` 的 `extra` 字段和环境变量，环境变量优先级高于配置文件；当未显式配置 `data_dir` 时，适配器 SHALL 使用与插件源码目录分离的默认运行态数据目录。resolver 相关环境变量 SHALL 明确区分生产默认行为与本地测试 override：生产默认不设置 `ANP_DID_RESOLVER_BASE_URL`，而是让 DID WBA resolver 按 DID domain/path 走 HTTPS 解析；`ANP_DID_RESOLVER_BASE_URL` 仅用于 loopback 本地开发、测试床与 E2E。Hermes tool RPC 相关配置 SHALL 默认关闭，并通过 `gateway.platforms.anp.extra` 中的显式开关、allowlist、denylist 和 caller DID 授权控制。

#### Scenario: 环境变量覆盖
- **WHEN** 同时设置了 `ANP_HOST` / `ANP_PORT` 环境变量和 `config.yaml` 中的 `host` / `port`
- **THEN** 使用环境变量的值

#### Scenario: data_dir 默认值
- **WHEN** 未设置 `ANP_DATA_DIR` 且 `config.yaml` 中未配置 `data_dir`
- **THEN** `data_dir` 使用 Hermes 用户数据目录下的 `anp-agent` 专用目录

#### Scenario: data_dir 配置文件覆盖
- **WHEN** `config.yaml` 的 `gateway.platforms.anp.extra.data_dir` 配置了路径且未设置 `ANP_DATA_DIR`
- **THEN** `data_dir` 使用配置文件中的路径

#### Scenario: data_dir 环境变量覆盖
- **WHEN** 同时设置了 `ANP_DATA_DIR` 和 `config.yaml` 中的 `data_dir`
- **THEN** `data_dir` 使用 `ANP_DATA_DIR` 的值

#### Scenario: resolver override 仅用于本地测试
- **WHEN** 运维配置 `ANP_DID_RESOLVER_BASE_URL`
- **THEN** 该值 SHALL 仅接受 loopback base URL
- **AND** 文档 SHALL 说明生产部署应让 DID Document 可通过 DID WBA 默认 HTTPS 规则解析，而不是依赖该 override

#### Scenario: tool RPC 默认关闭
- **WHEN** `gateway.platforms.anp.extra` 未配置 tool RPC
- **THEN** 适配器配置中的 tool RPC enabled 状态为 false
- **AND** 插件不暴露任何 Hermes tools

#### Scenario: tool RPC 配置文件启用
- **WHEN** `gateway.platforms.anp.extra.tool_rpc.enabled` 为 true 且配置了 allowlist 与 caller DID 授权
- **THEN** 适配器加载该配置供 server 构建 discovery、capabilities 和 RPC route 使用

#### Scenario: tool RPC 安全边界配置
- **WHEN** 运维配置 `allowed_tools`、`allowed_toolsets`、`denied_tools`、`allowed_dids`、`timeout_seconds` 或 `max_result_bytes`
- **THEN** 适配器 SHALL 保留这些配置并应用默认值与安全上限

### Requirement: send 桥接
适配器 SHALL 实现 `send(chat_id, content, ...)`，当 `chat_id` 以 `anp:` 前缀标识某次 JSON-RPC 调用的服务端内部 request id 时，将该调用标记为已完成并返回结果。

#### Scenario: 回复 ANP 调用
- **WHEN** Hermes 处理完 ANP 调用并通过 `send()` 向 `anp:{request_id}` 形式的 `chat_id` 发送回复
- **THEN** 适配器提取服务端内部 request id，并将对应的 JSON-RPC pending Future 设置为该回复内容

#### Scenario: 未知 request id 回复失败
- **WHEN** Hermes 通过 `send()` 回复的 `anp:{request_id}` 不存在或已完成
- **THEN** 适配器返回失败结果，不创建新的 pending Future

#### Scenario: 非 ANP chat_id 回复失败
- **WHEN** Hermes 通过 `send()` 回复的 `chat_id` 不以 `anp:` 为前缀
- **THEN** 适配器返回失败结果，不影响任何 ANP pending Future

### Requirement: JSON-RPC 错误响应契约
当 `/agent/rpc` 认证失败时，适配器 SHALL 返回 `plugins/anp-agent/auth.py` 中 `AuthenticationError` 所携带的 JSON-RPC 错误码与消息，并附带安全的 HTTP 响应头。

#### Scenario: 缺少签名返回 -32003
- **WHEN** 调用方未提供 `Signature` / `Signature-Input` 头
- **THEN** HTTP 响应状态码为 401，JSON-RPC `error.code` 为 `-32003`，`error.message` 为 `缺少认证头`

#### Scenario: DID 文档解析失败返回 -32002
- **WHEN** 调用方 DID 文档无法解析（超时、网络错误、默认 HTTPS 解析失败）
- **THEN** HTTP 响应状态码为 401，JSON-RPC `error.code` 为 `-32002`，`error.message` 为 `DID 文档无法解析`

#### Scenario: 内部认证错误返回 -32006
- **WHEN** 认证过程中出现未预期内部异常
- **THEN** HTTP 响应状态码为 500，JSON-RPC `error.code` 为 `-32006`，`error.message` 为 `认证服务内部错误`

### Requirement: Challenge 头转发
适配器 SHALL 在认证失败响应中转发来自 `DidWbaVerifierError` 的 `WWW-Authenticate` 和 `Accept-Signature` 头（如果存在）。

#### Scenario: 401 响应携带 challenge 头
- **WHEN** verifier 返回 401 并携带 `WWW-Authenticate` 头
- **THEN** `/agent/rpc` 的 401 HTTP 响应包含同名头且值不变

### Requirement: OpenSpec 状态说明
项目开发文档 SHALL 将已归档变更和当前活跃变更区分说明，不得将已归档的 `create-anp-hermes-plugin` 描述为当前进行中的变更。

#### Scenario: 查看项目开发指南
- **WHEN** 开发者阅读 `CLAUDE.md` 中的 OpenSpec 说明
- **THEN** 文档指向当前活跃变更或通用 OpenSpec 命令，而不是已归档的历史变更

### Requirement: JSON-RPC 成功响应契约
当 `/agent/rpc` 请求通过 DID WBA 认证并被 Hermes 成功处理，或被插件内置 ANP 方法成功处理时，适配器 SHALL 返回 JSON-RPC 2.0 成功响应，并安全附带认证成功响应头；当 bridge 处理失败时，适配器 SHALL 返回 JSON-RPC error 而不是成功响应。

#### Scenario: chat 成功响应
- **WHEN** 调用方发送合法且认证通过的 `chat` JSON-RPC 请求，且 Hermes 返回文本回复
- **THEN** HTTP 状态码为 200，响应体为 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`，其中 `id` 回显客户端 JSON-RPC `id`

#### Scenario: anp.get_capabilities 成功响应
- **WHEN** 调用方发送合法且认证通过的 `anp.get_capabilities` 请求
- **THEN** HTTP 状态码为 200，响应体为 JSON-RPC 成功响应，`result` 包含当前运行时能力信息

#### Scenario: 成功响应附带 Authentication-Info
- **WHEN** 认证器为成功认证生成 `Authentication-Info` 响应头，且请求被成功处理
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应包含该 `Authentication-Info` 头

#### Scenario: 成功响应不透传未允许头
- **WHEN** 认证器成功结果包含未列入允许列表的响应头
- **THEN** `/agent/rpc` 的 HTTP 200 成功响应不包含这些未允许头

#### Scenario: bridge 失败不返回成功响应
- **WHEN** 请求通过认证但 bridge 超时、取消或无法提交给 Hermes
- **THEN** `/agent/rpc` 返回 JSON-RPC `error`，响应体不包含 `result.response`

#### Scenario: bridge 失败不附带成功认证头
- **WHEN** 请求通过认证并生成 `Authentication-Info`，但 bridge 处理失败
- **THEN** `/agent/rpc` 的错误响应不包含成功认证 `Authentication-Info` 头

### Requirement: 运行时能力声明
适配器 SHALL 在运行时能力响应和 OpenRPC 文档中声明当前真实支持且已启用的 ANP Core Binding 与可选 Hermes tool RPC 能力，不得声明尚未实现的 Direct、Group 或 E2EE 能力。Hermes tools 方法只有在 tool RPC 显式开启且对应工具通过 allowlist、denylist、caller DID 授权和可用性校验时才可声明。

#### Scenario: 仅声明已支持 profiles
- **WHEN** 插件返回 `anp.get_capabilities`
- **THEN** `supported_profiles` 包含 `anp.core.binding.v1`，且不包含尚未实现的 Direct、Group 或 E2EE profile

#### Scenario: 默认不声明 Hermes tools 方法
- **WHEN** tool RPC 未启用或没有 allowlisted 可用工具
- **THEN** OpenRPC methods 列表不包含任何 `hermes.tool.*` 方法

#### Scenario: 声明已启用 Hermes tools 方法
- **WHEN** tool RPC 已启用且存在 allowlisted、未 denylisted、caller DID 授权且当前可用的 Hermes tool
- **THEN** OpenRPC methods 列表可以包含对应 `hermes.tool.<tool_name>` 方法
- **AND** 不包含未 allowlist、denylisted、未授权或当前不可用的工具方法
