## MODIFIED Requirements

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
