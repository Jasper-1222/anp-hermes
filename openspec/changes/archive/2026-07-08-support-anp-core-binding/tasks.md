## 1. Core Binding 解析与错误模型

- [x] 1.1 在 `tests/test_server.py` 增加 Core Binding envelope 中 `params.body.message` 作为 chat 文本的测试。
- [x] 1.2 在 `tests/test_server.py` 增加 `params.body.message` 优先于 legacy `params.message` 的测试。
- [x] 1.3 在 `tests/test_server.py` 增加 invalid envelope shape 返回 `1003` / `anp.invalid_params_shape` 的测试。
- [x] 1.4 在 `tests/test_server.py` 增加 unsupported profile 返回 `1001` / `anp.unsupported_profile` 的测试。
- [x] 1.5 在 `tests/test_server.py` 增加 unsupported security profile 返回 `1002` / `anp.unsupported_security_profile` 的测试。
- [x] 1.6 在 `server.py` 增加可选 `error.data` 的 JSON-RPC error 构造支持。
- [x] 1.7 在 `server.py` 增加 Core Binding params 解析/校验辅助函数，保持 legacy `params.message` 兼容。

## 2. anp.get_capabilities 方法

- [x] 2.1 在 `tests/test_server.py` 增加 `anp.get_capabilities` 成功响应测试，覆盖 `service_did`、`supported_profiles`、`supported_security_profiles`、`limits`、`supported_content_types`。
- [x] 2.2 在 `tests/test_server.py` 增加 `anp.get_capabilities` 不调用 bridge message handler 的测试。
- [x] 2.3 在 `server.py` 增加 capabilities 构造函数，使用当前 `ANPIdentity.did` 和 HTTP 请求体限制。
- [x] 2.4 在 `_handle_rpc()` 中增加 `anp.get_capabilities` 方法路由，并保持认证成功响应头行为。

## 3. OpenRPC 更新

- [x] 3.1 在 `tests/test_server.py` 扩展 `GET /agent/interface.json` 测试，验证包含 `chat` 与 `anp.get_capabilities`。
- [x] 3.2 在 `server.py` 更新 `_build_openrpc_json()`，声明 `chat` 支持 legacy `params.message` 与 Core Binding `params.body.message`。
- [x] 3.3 在 `server.py` 更新 `_build_openrpc_json()`，声明 `anp.get_capabilities` 方法与 capability negotiation 返回结构。

## 4. 验证与状态记录

- [x] 4.1 运行 `openspec validate support-anp-core-binding --strict` 并修正 delta specs 问题。
- [x] 4.2 运行 `python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v`。
- [x] 4.3 运行 `cd plugins/anp-agent && ruff check . && black --check .`。
- [x] 4.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `support-anp-core-binding` 为当前 active change 与验证状态。
