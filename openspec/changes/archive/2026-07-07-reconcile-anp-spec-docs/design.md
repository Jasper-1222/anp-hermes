## Context

`anp-agent` 当前已经能作为 Hermes 平台插件运行，并完成最小 ANP/OpenANP 链路：DID WBA 身份生成、`/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`、DID WBA HTTP Message Signatures 认证和 `chat` 到 Hermes `MessageEvent` 的桥接。

本变更不解决运行时代码问题，而是先校准规格与文档。当前存在几类容易误导后续开发的偏差：

- 归档后的主 specs 仍有 `Purpose: TBD`。
- `anp-rpc-bridge` 对正常响应的描述仍是裸字符串 `result`，而当前实现和 E2E 使用 `result.response`。
- `anp-identity` 仍要求写入 `agent.json`，但当前实现只持久化 DID 文档和私钥 PEM。
- `anp-auth-error-classification` 要求 `AuthenticationError.cause`，但当前实现没有该字段，场景描述也只要求 `status_code`、`rpc_code`、`message` 与可选 `headers`。
- README/CLAUDE 仍将 DID 文档公开路径描述为 `/.well-known/did.json`，但当前 DID 为 path DID，实际路径由 DID path segments 推导，例如 `/agent/e1_<fingerprint>/did.json`。
- 已完成且已有 archive 副本的变更仍残留在 active `openspec/changes/` 目录。

## Goals / Non-Goals

**Goals:**

- 让 README、CLAUDE、OpenSpec 主规格与当前已实现的最小链路保持一致。
- 把“当前已实现契约”和“后续待实现增强”分开，避免把后续 P0/P1 代码修复误写成当前已有能力。
- 修正 path DID 文档路径说明。
- 修正 JSON-RPC 正常响应 shape 说明。
- 移除或降级未实现的 `agent.json` 和 `AuthenticationError.cause` 强制要求。
- 清理 OpenSpec active/archive 状态。
- 为后续 `protect-anp-runtime-secrets`、`return-authentication-info`、`harden-rpc-bridge` 等实现型变更提供稳定基线。

**Non-Goals:**

- 不修改 `plugins/anp-agent` 运行时代码。
- 不实现 `Authentication-Info` 成功响应头。
- 不修复 RPC bridge 超时、pending key 或 JSON-RPC id 问题。
- 不新增 `/.well-known/agent-descriptions`。
- 不新增 `anp.get_capabilities`。
- 不更改默认 `data_dir` 或删除/迁移当前工作区中的未跟踪密钥文件。
- 不做插件包化或 resolver monkeypatch 重构。

## Decisions

### 决策 1：本变更只做规格/文档基线校准

后续分析发现的问题横跨协议、并发、安全和工程化。若在一个 change 中同时修文档和运行时代码，会使 review 和验证范围过大。本变更先把现有契约写准，后续每个 P0/P1 运行时问题再通过独立 OpenSpec change 处理。

替代方案：直接在本变更中修复 `Authentication-Info`、bridge 超时与 pending key。拒绝原因：这些属于行为变更，需要独立设计、测试和回归。

### 决策 2：将 DID 文档路径描述修正为 path DID 规则

当前身份生成使用 DID WBA path DID，例如 `did:wba:localhost:agent:e1_<fingerprint>`。按照 DID WBA 解析规则，其文档路径应是 `/{path...}/did.json`，即 `/agent/e1_<fingerprint>/did.json`。`/.well-known/did.json` 只适用于裸域 DID，不应作为当前默认路径描述。

替代方案：在本变更中要求代码额外注册 `/.well-known/did.json`。拒绝原因：这会改变运行时 API，且不符合当前 path DID 默认身份形态；如需裸域 DID 支持，应另起变更。

### 决策 3：当前 RPC result 契约采用 `result.response`

当前 `server.py` 和 E2E 规格均使用：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "response": "..."
  },
  "id": "..."
}
```

因此主规格应描述为 `result.response`，避免与现有实现和测试冲突。

替代方案：把实现改回裸字符串 `result`。拒绝原因：本变更不改业务代码；同时对象 result 更利于后续扩展元数据。

### 决策 4：移除当前阶段对 `agent.json` 的强制要求

当前实现没有 `agent.json` 持久化逻辑，现有发现端点也不依赖本地 `agent.json`。因此 `agent.json` 不应在当前主规格中作为必需产物。若未来需要将 Agent Description 本地缓存为文件，应通过新 change 明确 schema、用途和与 `/agent/ad.json` 的关系。

替代方案：在本变更中实现 `agent.json`。拒绝原因：这属于新增持久化行为，不是文档校准。

### 决策 5：`AuthenticationError.cause` 不作为当前强制契约

当前实现的 `AuthenticationError` 携带 `status_code`、`rpc_code`、`message` 与 `headers`，没有 `cause`。主规格应描述当前对 server 构造响应真正需要的字段。原始异常追踪可作为未来内部可观测性增强，不作为当前对外契约。

替代方案：在本变更中实现 `cause`。拒绝原因：这会改变代码和测试，不属于当前文档校准范围。

### 决策 6：已归档变更残留按目录卫生清理

对于已经存在 archive 副本且任务已完成的 active 目录，应从 active `openspec/changes/` 中移除，避免 `openspec list` 和后续代理误判仍有待实施任务。

替代方案：保留 active 目录但在任务中说明已完成。拒绝原因：OpenSpec active 区语义应表示正在推进或待推进的变更。

## Risks / Trade-offs

- **[Risk] 文档校准可能暴露当前实现尚未达到社区级协议完整性。** → Mitigation：在 README/规格中明确本期为最小链路，`Authentication-Info`、ANP-07/08、Core Binding 等进入后续 change。
- **[Risk] 移除 `agent.json` 强制要求可能遗漏未来需要。** → Mitigation：仅从当前强制契约中移除；未来如需要本地 Agent Description 缓存，可通过独立 change 重新引入。
- **[Risk] `AuthenticationError.cause` 降级后，内部排错字段不被规格约束。** → Mitigation：认证错误分类仍保留 `status_code`、`rpc_code`、`headers` 和安全响应约束；cause 可在后续可观测性增强中重新设计。
- **[Risk] 清理 active 目录可能影响未提交的历史残留文件。** → Mitigation：仅清理已确认有 archive 副本、tasks 全部完成且不包含未归档 spec delta 的目录；清理前读取对应文件确认内容重复。
