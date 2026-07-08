## Why

当前 `/agent/rpc` 已完成基础 JSON-RPC 2.0 收紧与 bridge 加固，但仍只支持历史简化形态 `params.message` 和单一 `chat` 方法。ANP Core Binding 要求统一使用 `params.meta/body` envelope，并通过 `anp.get_capabilities` 暴露运行时能力；缺少这些会限制与标准 ANP 客户端的互通。

## What Changes

- 新增 ANP Core Binding 最小兼容能力，支持 `anp.core.binding.v1` 的运行时能力协商。
- 新增 `anp.get_capabilities` JSON-RPC 方法，返回 service DID、supported profiles、supported security profiles、limits 与 supported content types。
- `chat` 方法兼容 Core Binding envelope：优先从 `params.body.message` 读取文本，同时保留当前 `params.message` 作为过渡兼容。
- 校验 Core Binding 请求中的 `params.meta.profile`、`params.meta.security_profile` 与 `params.body` 基本形态，并为不支持的 profile/security profile 返回明确 JSON-RPC error。
- 更新 OpenRPC 文档，声明 `chat` 支持 legacy 与 Core Binding params 形态，并声明 `anp.get_capabilities`。
- 增加 server/integration 测试，覆盖 capabilities、`params.body.message`、unsupported profile/security profile、invalid params shape。
- 不新增 discovery endpoint，不扩展 Agent Description，不暴露 Hermes tools，不实现 Direct/Group/E2EE 业务 profiles。

## Capabilities

### New Capabilities

- `anp-core-binding`: 定义本插件对 `anp.core.binding.v1` 的最小兼容契约，包括 capabilities、`params.meta/body` envelope、profile/security profile 校验与 Core Binding 错误语义。

### Modified Capabilities

- `anp-rpc-bridge`: 增加 `anp.get_capabilities` 方法路由，兼容 `params.body.message`，并明确 Core Binding 参数错误映射。
- `anp-platform-adapter`: 增加运行时能力声明契约，使适配器声明当前支持的 ANP profiles、security profiles、limits 与 content types。
- `anp-discovery`: 更新 OpenRPC 文档契约，声明 `chat` 的 Core Binding 参数形态与 `anp.get_capabilities` 方法。

## Impact

- 代码：`plugins/anp-agent/server.py`，必要时小幅调整常量或辅助函数。
- 测试：`plugins/anp-agent/tests/test_server.py`，必要时补充 `tests/test_integration.py`。
- API 行为：新增 `anp.get_capabilities` 成功响应；`chat` 继续支持现有 `params.message`，并新增 `params.body.message` 支持。
- 兼容性：不破坏当前 `chat` 成功响应 `result.response` shape；legacy 调用保持可用。