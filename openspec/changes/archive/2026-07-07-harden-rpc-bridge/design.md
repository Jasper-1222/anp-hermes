## Context

`harden-rpc-bridge` 是前三个 P0 变更后的下一步正确性加固。当前实现已经具备 DID WBA 身份、认证错误分类、成功 `Authentication-Info` 返回和最小 JSON-RPC `chat` 链路，但 bridge/server 边界仍有几个协议与并发问题：

- `/agent/rpc` 只检查 `id`、`method`、`params` 的基本存在和类型，没有强制 `jsonrpc == "2.0"`，也没有拒绝 batch、notification 或非字符串 `id`。
- `ANPBridge.call()` 把超时、取消、handler 提交失败等失败路径转成普通字符串，server 再包装为成功 `result.response`。
- pending Future 以客户端 `rpc_id` 作为全局 key；不同 caller 或并发请求复用相同 `id` 时会冲突。
- Hermes `chat_id` 由客户端 `rpc_id` 派生，数字 id 或复杂 id 会导致关联语义不稳定。

本设计只处理 bridge 与 JSON-RPC 边界的正确性，不扩展 ANP Core Binding 的新能力。

## Goals / Non-Goals

**Goals:**

- 让 `/agent/rpc` 的请求校验更明确：只接受单个 JSON-RPC 2.0 request object、非空字符串 `id`、字符串 `method`、对象 `params`。
- 让 bridge 失败路径返回 JSON-RPC `error`，而不是成功 `result.response`。
- 将 pending Future 关联 key 从客户端 `rpc_id` 改为服务端内部 request id，避免跨 caller/跨请求冲突。
- 保持成功响应中的 JSON-RPC `id` 回显客户端原始字符串 id。
- 保持当前外部成功响应 shape：`result.response`。
- 增加单元测试覆盖请求校验、内部 request id、重复客户端 id 并发、超时/取消/handler 异常。

**Non-Goals:**

- 不实现 `anp.get_capabilities`。
- 不支持 batch JSON-RPC。
- 不支持 notification（缺少 `id` 的请求）。
- 不引入 `params.meta/body` 兼容；仍以当前 `params.message` 作为 `chat` 文本来源。
- 不改变 DID WBA 认证流程、认证错误码或 `Authentication-Info` 行为。
- 不重构 Hermes 插件注册或包结构。

## Decisions

### 1. JSON-RPC `id` 只接受非空字符串

本变更将 `/agent/rpc` 的 `id` 策略收紧为非空字符串。JSON-RPC 2.0 本身允许 string/number/null，但当前 bridge 会把 id 同时用于 pending key、Hermes `message_id`、`chat_id` 派生和日志追踪。继续接受数字 id 会让内部关联出现隐式字符串化边界，且不符合当前路线图中“建议只接受非空字符串 id”的 P0 目标。

备选方案：接受 number 并统一转换为字符串。该方案兼容面更宽，但会让响应 `id` 回显类型、内部 key 类型和 chat_id 语义更复杂，且无法解决客户端重复 id 的并发冲突本质。因此本阶段选择更简单、可测试的非空字符串策略。

### 2. 错误响应 id 规则

请求未通过合法非空字符串 `id` 校验时，JSON-RPC error response 的 `id` 为 `null`；请求已经通过 `id` 校验后发生 method、params、认证后 bridge 等错误时，error response 的 `id` 回显客户端 JSON-RPC `id`。这样既避免回显不可信或无法关联的 id，又让已经建立关联的请求能被客户端稳定匹配。

备选方案：尽量回显请求体中的任意 `id` 值。该方案更接近部分 JSON-RPC 实现的宽松行为，但会在本变更明确拒绝数字、对象、数组、空字符串 id 时重新暴露不稳定关联值。因此本阶段选择 `id` 校验通过后才回显。

### 3. 引入服务端内部 request id

`ANPBridge.call()` 在每次调用时生成内部 request id，例如 `req-<递增序号>`。该 id 用于：

- `_pending` 字典 key。
- `MessageEvent.message_id`。
- `_build_source(...).chat_id` 中的 `anp:<internal_request_id>`。
- `metadata["anp_request_id"]`。
- `ANPAdapter.send()` 从 `chat_id` 提取并传给 `bridge.set_result()`。

客户端 JSON-RPC `id` 保留在 `metadata["anp_rpc_id"]`，server 成功或失败响应仍回显客户端 `id`。

备选方案：将 pending key 改为 `(caller_did, rpc_id)`。该方案能缓解不同 caller 使用相同 id 的冲突，但同一 caller 并发复用 id 仍会冲突，并且 `chat_id` 仍暴露客户端 id。内部 request id 更彻底，也更接近服务端 correlation id 模式。

### 4. Bridge 使用结构化异常表达失败

新增轻量的 bridge 异常类型（例如 `ANPBridgeError`），携带 JSON-RPC 错误码和对外消息。`ANPBridge.call()` 在以下路径抛出结构化异常：

- handler 提交失败。
- pending 容量耗尽。
- 等待 Hermes 回复超时。
- Future 被取消或 bridge 停止。
- 等待结果时出现未预期异常。

`server._handle_rpc()` 捕获该异常并返回 JSON-RPC `error`。默认错误码使用 `-32603`，消息按场景区分为“请求处理超时”“请求已取消”“请求处理过程中发生内部错误”等。对于 `asyncio.CancelledError`，实现 SHALL 区分 pending Future 被取消与当前处理协程被外部取消：前者映射为 `ANPBridgeError(-32603, "请求已取消")`，后者保留 asyncio cancellation 语义并继续抛出，避免吞掉服务关闭或上层取消信号。

备选方案：让 `bridge.call()` 返回 `Result` union。该方案避免异常控制流，但需要改动 call site 和测试较多，且当前 server 已有异常到 JSON-RPC error 的映射模式。结构化异常更小、更符合现有代码。

### 5. 失败响应不附带成功认证头

即使认证成功后 bridge 失败，也不返回成功认证 `Authentication-Info`。当前 server 已经只在最终成功响应中设置 `auth_result.headers`，本变更保持该行为，避免把“认证成功头”和“业务处理成功”混淆。

### 6. 保持 `chat` 成功路径最小改动

`params.message` 仍作为 Hermes 消息文本，`method != "chat"` 仍返回 `-32601`，成功响应仍是 `{"result":{"response":"..."}}`。更完整的 ANP Core Binding（`params.body.message`、`anp.get_capabilities`）留给后续 `support-anp-core-binding`。

## Risks / Trade-offs

- **兼容性收紧：部分 JSON-RPC 客户端使用数字 id。** → 本项目当前参考实现优先保障 bridge 正确性；文档和 spec 明确只接受非空字符串 id，调用方可改用字符串 id。
- **内部 request id 改动会影响 adapter/bridge 测试。** → 同步更新 `test_bridge.py` 与 `test_adapter.py`，通过事件 metadata 和 chat_id 行为验证新关联方式。
- **handler 异常从成功文本变为 JSON-RPC error。** → 这是目标行为；server 测试需从 `result.response` 断言改为 `error.code == -32603`。
- **Future 清理与 stop 取消可能暴露等待任务时序。** → 测试中使用短 timeout 和 `await asyncio.sleep(0)` 让任务观察取消，保持现有异步测试风格。

## Migration Plan

1. 先补充或调整测试，锁定新行为：严格 JSON-RPC id、重复客户端 id 并发、bridge 超时/取消/handler 异常返回 error。
2. 修改 `bridge.py`：新增内部 request id、结构化异常、pending key 迁移。
3. 修改 `adapter.py`：保持 `anp:` chat_id 入口，但提取内部 request id 调用 `set_result()`。
4. 修改 `server.py`：强化 `_parse_rpc_request()`，捕获 bridge 结构化异常并映射 JSON-RPC error。
5. 运行 targeted tests 与 lint/format。

回滚策略：若新行为导致 E2E 不兼容，可回退本 change 的代码和 spec；前三个 P0 变更不依赖内部 request id。

## Open Questions

无阻塞问题。当前设计明确选择非空字符串 id 和内部 request id；对数字 id、batch、notification 的支持留给未来兼容性评估。