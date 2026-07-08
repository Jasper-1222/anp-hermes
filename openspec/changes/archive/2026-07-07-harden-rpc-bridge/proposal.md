## Why

当前 `/agent/rpc` 到 Hermes 的桥接层仍把超时、取消和 handler 提交失败等内部异常包装成成功的 `result.response`，会让调用方误判请求成功。同时 pending Future 仅按客户端传入的 `rpc_id` 全局索引，且 JSON-RPC `id` 未收紧为稳定字符串，存在跨调用冲突、数字 id 与 Hermes `chat_id` 关联不一致等并发正确性风险。

## What Changes

- 收紧 `/agent/rpc` 的 JSON-RPC 请求校验：明确只接受单个 JSON-RPC 2.0 对象、非空字符串 `id`、字符串 `method`、对象 `params`，并拒绝 batch、notification 和无效 `jsonrpc` 版本。
- 将 bridge 超时、取消、handler 提交失败、pending 容量耗尽等失败路径改为结构化错误，不再返回成功 `result.response`。
- 为 bridge 引入服务端内部 request id，用于 pending Future、Hermes `message_id`、`SessionSource.chat_id` 和 `adapter.send()` 关联，避免直接把客户端 `rpc_id` 当作全局 pending key。
- 保持 JSON-RPC 成功响应中的 `id` 回显客户端原始 `id`，同时将内部 request id 放入事件元数据，便于追踪和回传。
- 增加 bridge、adapter、server 测试，覆盖重复客户端 id 并发调用、无效 JSON-RPC 请求、超时、取消和 handler 异常的 JSON-RPC error 行为。
- 不新增 ANP 方法，不实现 `anp.get_capabilities`，不改变当前 `chat` 成功响应的 `result.response` shape。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `anp-rpc-bridge`: 收紧 JSON-RPC 请求接收、异步响应桥接和 pending Future 关联语义。
- `anp-platform-adapter`: 调整 `send` 桥接契约，明确使用服务端内部 request id 关联 ANP 调用结果。

## Impact

- 代码：`plugins/anp-agent/server.py`、`plugins/anp-agent/bridge.py`、`plugins/anp-agent/adapter.py`。
- 测试：`plugins/anp-agent/tests/test_server.py`、`plugins/anp-agent/tests/test_bridge.py`、`plugins/anp-agent/tests/test_adapter.py`，必要时补充 integration 覆盖。
- API 行为：无效 JSON-RPC 请求更严格地返回 `-32600`，bridge 失败路径返回 JSON-RPC `error`（默认 `-32603`）而不是成功 `result.response`。
- 兼容性：成功 `chat` 请求的响应体保持 `{"jsonrpc":"2.0","result":{"response":"..."},"id":...}`；本变更不引入新的外部依赖。
