## Context

`support-anp-core-binding` 是前四个 P0 正确性修复之后的协议互通增强。当前实现已经具备：

- DID WBA 身份与认证。
- `/agent/rpc` JSON-RPC 2.0 基础校验。
- 非空字符串 `id`、禁止 batch/notification。
- bridge 内部 request id 与结构化错误。
- 成功认证 `Authentication-Info` 响应头。

但当前业务参数仍是历史简化形态：

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "chat",
  "params": {"message": "hello"}
}
```

ANP Core Binding v1.1 要求统一外层 envelope：

```json
{
  "params": {
    "meta": {
      "profile": "anp.core.binding.v1",
      "security_profile": "transport-protected"
    },
    "body": {"...": "..."}
  }
}
```

同时，ANP endpoint MUST expose capability negotiation method `anp.get_capabilities`。本变更在不扩展 Direct/Group/E2EE 业务 profile 的前提下，补齐最小 Core Binding 互通面。

## Goals / Non-Goals

**Goals:**

- 支持 `anp.get_capabilities` 方法，返回当前运行时服务 DID、支持的 profiles/security profiles、limits 与 content types。
- 支持 `chat` 从 `params.body.message` 读取文本。
- 保留现有 `params.message` legacy 调用，避免破坏当前 demo/E2E 链路。
- 对 Core Binding envelope 做最小校验：`params.meta`、`params.body`、`meta.profile`、`meta.security_profile`。
- 对不支持的 profile/security profile 返回明确 JSON-RPC error，并携带机器可读 `error.data.anp_code`。
- 更新 OpenRPC，使调用方能发现 `chat` 与 `anp.get_capabilities`。

**Non-Goals:**

- 不实现 Direct Base、Group Base、Direct E2EE、Group E2EE。
- 不实现完整 `meta.target`、`operation_id`、`message_id`、idempotence 存储。
- 不新增 `/.well-known/agent-descriptions`。
- 不扩展 Agent Description 字段。
- 不暴露 Hermes tools/skills。
- 不实现 Bearer token 后续请求验收逻辑。

## Decisions

### 1. Core Binding envelope 作为新增兼容形态，而不是替换 legacy params

`chat` 同时支持两种输入：

```json
{"params": {"message": "hello"}}
```

和：

```json
{
  "params": {
    "meta": {
      "profile": "anp.core.binding.v1",
      "security_profile": "transport-protected"
    },
    "body": {"message": "hello"}
  }
}
```

优先读取 `params.body.message`；如果不存在，再回退到 `params.message`。这样既能让标准客户端使用 Core Binding envelope，也不会破坏当前 ANP demo client / E2E 的简化 `chat` 路径。

备选方案：强制废弃 `params.message`。该方案更纯粹，但会把兼容性风险和测试床迁移成本集中到一个 P1 变更中，不符合本项目“参考实现逐步增强”的路线。

### 2. `anp.get_capabilities` 走同一个 `/agent/rpc` 入口和认证链路

虽然 ANP Core Binding 允许 capability negotiation 作为匿名公共发现能力，但当前 `/agent/rpc` 统一由 DID WBA 认证保护。本变更不改变认证边界：`anp.get_capabilities` 也需要通过现有认证流程。

原因：

- 认证边界调整会影响 security model，超出本变更范围。
- 当前插件已有 `/agent/ad.json` 和 `/agent/interface.json` 作为公开发现入口。
- 如果后续要支持匿名 capabilities，应作为单独变更讨论认证绕过、缓存与信息披露边界。

### 3. capabilities 返回最小运行时权威信息

`anp.get_capabilities` 返回：

```json
{
  "service_did": "did:wba:...",
  "supported_profiles": ["anp.core.binding.v1"],
  "supported_security_profiles": ["transport-protected"],
  "limits": {
    "max_request_bytes": "1048576"
  },
  "supported_content_types": ["text/plain", "application/json"]
}
```

`service_did` 使用当前 `ANPIdentity.did`。`limits.max_request_bytes` 与 server `client_max_size` 保持一致，用 decimal string 表示。暂不声明 Direct/Group profiles，避免让调用方误以为本插件已经支持标准 Direct Base 方法。

### 4. Core Binding 错误使用 JSON-RPC error，最小补充 `data.anp_code`

现有 JSON-RPC error 构造只有 `code/message`。本变更新增可选 `data` 参数，用于 Core Binding 相关错误：

- `anp.unsupported_profile`
- `anp.unsupported_security_profile`
- `anp.invalid_params_shape`

错误码使用 ANP public error code：

- `1001` unsupported profile
- `1002` unsupported security profile
- `1003` invalid params shape

保留现有认证错误码和 bridge 错误码不变，避免把历史自定义认证错误一起迁移到 ANP public error model。

### 5. envelope 校验只针对 Core Binding 形态

如果 `params` 包含 `meta` 或 `body`，按 Core Binding envelope 校验：

- `meta` MUST 是对象。
- `body` MUST 是对象。
- `meta.profile` MUST 是 `anp.core.binding.v1`。
- `meta.security_profile` MUST 是 `transport-protected`。

如果 `params` 不包含 `meta/body`，按 legacy `chat` 参数处理。这避免把 legacy 请求误判为无效 Core Binding 请求。

### 6. OpenRPC 只描述当前支持方法，不提前承诺后续 profiles

`/agent/interface.json` 增加：

- `chat` 参数说明：支持 legacy `message` 与 Core Binding `meta/body` envelope。
- `anp.get_capabilities` 方法。

不把 Direct/Group/E2EE 方法写入 OpenRPC，不把 Hermes tools 暴露为方法。

## Risks / Trade-offs

- **capabilities 仍要求认证，和 ANP 匿名公共发现建议不完全一致。** → 本变更不改变认证边界；后续可在独立 change 中评估匿名 capabilities。
- **同时支持 legacy 与 Core Binding 会增加解析分支。** → 解析逻辑保持在 server 辅助函数中，测试覆盖两种路径；后续若要废弃 legacy 可单独变更。
- **只声明 `anp.core.binding.v1` 可能显得能力少。** → 这是当前真实能力，避免误导标准客户端调用未实现的 Direct/Group 方法。
- **Core Binding 错误模型与既有认证错误码并存。** → 本变更只对新增 Core Binding 错误使用 ANP public error code；认证错误保持现有已归档契约。

## Migration Plan

1. 增加 server 测试：`anp.get_capabilities`、`chat` 的 `params.body.message`、unsupported profile/security profile、invalid envelope shape。
2. 在 `server.py` 增加 Core Binding 常量、capabilities 构造、JSON-RPC error data 支持、params 解析辅助函数。
3. 更新 `_handle_rpc()` 方法路由：`anp.get_capabilities` 直接返回 capabilities；`chat` 使用统一消息提取函数。
4. 更新 `_build_openrpc_json()`，声明新增方法和参数形态。
5. 运行 targeted tests、OpenSpec validate、lint/format。

回滚策略：如果标准客户端兼容性出现问题，可回退本 change；legacy `params.message` 路径不依赖本变更。

## Open Questions

无阻塞问题。匿名 `anp.get_capabilities`、Direct Base 方法和 well-known discovery 均留给后续变更。