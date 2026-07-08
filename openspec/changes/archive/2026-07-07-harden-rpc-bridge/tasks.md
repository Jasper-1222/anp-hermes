## 1. JSON-RPC 请求校验

- [x] 1.1 在 `tests/test_server.py` 增加无效 `jsonrpc` 版本返回 HTTP 400 / `-32600` 的测试。
- [x] 1.2 在 `tests/test_server.py` 增加 batch 请求返回 HTTP 400 / `-32600` 且不认证的测试。
- [x] 1.3 在 `tests/test_server.py` 增加缺少 `id`、空字符串 `id`、数字 `id` 返回 HTTP 400 / `-32600` 的测试。
- [x] 1.4 在 `server.py` 强化 `_parse_rpc_request()`：只接受对象、`jsonrpc == "2.0"`、非空字符串 `id`、字符串 `method`、对象 `params`。

## 2. Bridge 结构化错误

- [x] 2.1 在 `bridge.py` 新增 bridge 结构化异常类型，携带 JSON-RPC 错误码与对外消息。
- [x] 2.2 将 `ANPBridge.call()` 的 handler 异常、pending 容量耗尽、超时、取消和未预期异常改为抛出结构化异常。
- [x] 2.3 在 `server.py` 捕获 bridge 结构化异常，并返回 JSON-RPC `error` 而不是成功 `result.response`。
- [x] 2.4 调整 `tests/test_bridge.py` 中超时、stop 取消、handler 异常和 pending 容量耗尽的断言，验证结构化异常。
- [x] 2.5 调整 `tests/test_server.py` 中 bridge 超时/异常路径，验证 HTTP 200 / JSON-RPC `-32603` error 且不返回 `Authentication-Info`。

## 3. 内部 request id 与 pending 隔离

- [x] 3.1 在 `bridge.py` 为每次调用分配服务端内部 request id，并使用该 id 作为 `_pending` key、`MessageEvent.message_id` 和 `SessionSource.chat_id` 的来源。
- [x] 3.2 在 `MessageEvent.metadata` 中同时保留客户端 JSON-RPC `id`、服务端内部 request id、method、params、caller DID。
- [x] 3.3 保持 `ANPAdapter.send()` 从 `anp:{request_id}` 提取 request id 并调用 `bridge.set_result()`，更新命名和错误信息中的 `rpc_id` 表述。
- [x] 3.4 在 `tests/test_bridge.py` 增加相同客户端 `rpc_id` 并发调用互不覆盖的测试。
- [x] 3.5 更新 `tests/test_adapter.py`，验证 `send()` 使用内部 request id 设置 bridge 结果，并覆盖未知 request id / 非 ANP chat id。

## 4. 验证与文档状态

- [x] 4.1 运行 `openspec validate harden-rpc-bridge --strict` 并修正 delta specs 问题。
- [x] 4.2 运行 `python3 -m pytest plugins/anp-agent/tests/test_bridge.py plugins/anp-agent/tests/test_adapter.py plugins/anp-agent/tests/test_server.py -v`。
- [x] 4.3 运行 `cd plugins/anp-agent && ruff check . && black --check .`。
- [x] 4.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `harden-rpc-bridge` 为当前 active change 与验证状态。
