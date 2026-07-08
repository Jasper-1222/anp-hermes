## Why

当前 `anp-agent` 只通过 ANP 暴露 `chat` 与 `anp.get_capabilities`，外部智能体无法以结构化 RPC 方式调用 Hermes 已注册的 tools / skills。作为社区参考实现的下一步能力增强，需要在不开放高风险操作、不绕过 Hermes 权限边界的前提下，将明确允许的 Hermes 工具能力映射为 ANP OpenRPC methods。

## What Changes

- 新增 Hermes tools 暴露能力：从 Hermes 可用工具注册表中发现可暴露工具，并通过配置 allowlist 控制对外开放范围。
- 在 `/agent/interface.json` 的 OpenRPC 文档中动态声明 allowlisted tool methods，保持 `chat` 与 `anp.get_capabilities` 兼容。
- 在 `/agent/ad.json` 与 `anp.get_capabilities` 中只声明当前真实启用的 tools 能力，不声明未授权或不可用工具。
- 扩展 `/agent/rpc` 方法路由，将 allowlisted tool method 调度到 Hermes 工具执行路径，并把结果封装为 JSON-RPC 2.0 响应。
- 为工具调用增加安全边界：默认不暴露任何工具、拒绝高风险/未 allowlist 工具、保留 DID WBA 认证、提供审计元数据和结构化错误映射。
- 增加单元与集成测试，覆盖 OpenRPC 动态声明、allowlist、未知/未授权工具拒绝、成功工具调用和错误映射。
- 不实现 AP2、E2EE、Direct/Group profile，也不暴露文件删除、shell、外部发布等高风险工具。

## Capabilities

### New Capabilities
- `anp-hermes-tool-exposure`: 定义 Hermes tools / skills 通过 ANP OpenRPC methods 安全暴露、allowlist、调用调度、审计元数据与错误映射的行为契约。

### Modified Capabilities
- `anp-discovery`: OpenRPC、Agent Description 与能力声明需要从“不得声明 Hermes tools”调整为“仅声明已启用且 allowlisted 的 Hermes tools”。
- `anp-rpc-bridge`: `/agent/rpc` 方法路由需要支持 allowlisted tool methods，并对未授权、不可用或执行失败的工具调用返回结构化 JSON-RPC error。
- `anp-platform-adapter`: 平台配置需要支持 tools 暴露开关与 allowlist，且保持默认关闭、环境/配置来源边界清晰。

## Impact

- 影响插件运行时代码：`plugins/anp-agent/anp_agent/server.py`、`bridge.py`、`adapter.py`、`config.py`，并可能新增一个轻量 tools registry/dispatcher 模块。
- 影响公开 ANP API：`GET /agent/interface.json`、`GET /agent/ad.json`、`POST /agent/rpc`、`anp.get_capabilities` 的能力声明与方法路由。
- 影响测试：新增 server / bridge / adapter / config 相关测试，必要时增加 hermetic 集成测试 fixture 验证 tools allowlist 与调用路径。
- 不新增外部依赖，不修改 Hermes 核心，不改变现有 `chat`、`anp.get_capabilities`、DID WBA 认证和 discovery 基础契约。
