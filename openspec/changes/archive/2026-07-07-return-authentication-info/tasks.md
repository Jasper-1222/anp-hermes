## 1. 认证结果结构

- [x] 1.1 在 `plugins/anp-agent/auth.py` 中新增认证成功结果结构，包含 `caller_did` 与可转发响应头。
- [x] 1.2 从 verifier `verify_request()` 结果中读取 `response_headers`，按大小写不敏感匹配只提取 `Authentication-Info`。
- [x] 1.3 将 `ANPAuth.authenticate()` 返回值从 DID 字符串改为认证成功结果结构。
- [x] 1.4 确认认证失败的 `AuthenticationError`、错误分类和 challenge 头行为不变。

## 2. HTTP 响应转发

- [x] 2.1 更新 `plugins/anp-agent/server.py`，使用 `auth_result.caller_did` 调用 bridge。
- [x] 2.2 在 `/agent/rpc` 成功 JSON-RPC 响应中附带非空的 `Authentication-Info` 响应头。
- [x] 2.3 确认方法不存在、bridge 异常、认证失败等非成功业务响应不新增成功认证响应头。
- [x] 2.4 确认 JSON-RPC 成功响应体仍保持 `result.response` shape 不变。

## 3. 测试

- [x] 3.1 更新现有 `mock_auth.authenticate` 测试返回值，适配新的认证成功结果结构。
- [x] 3.2 增加 `test_auth.py` 测试，验证成功认证返回 caller DID 与过滤后的 `Authentication-Info`。
- [x] 3.3 增加 `test_server.py` 测试，验证 `/agent/rpc` 成功响应携带 `Authentication-Info`。
- [x] 3.4 增加或调整测试，验证无认证成功头时不返回空 `Authentication-Info`，且未允许头不透传。
- [x] 3.5 回归认证失败 challenge 头测试，确认失败路径不受影响。

## 4. 文档与规格状态

- [x] 4.1 更新 `README.md`，将 `Authentication-Info` 从后续待办中移除或改为已支持能力。
- [x] 4.2 更新 `plugins/anp-agent/README.md`，说明成功认证后通过 `Authentication-Info` 返回认证信息。
- [x] 4.3 更新 `docs/anp-hermes-openspec-execution-state.md`，记录当前 active change 和目标。

## 5. 验证

- [x] 5.1 运行 `openspec validate return-authentication-info --strict` 并修正规格问题。
- [x] 5.2 运行认证与 server 相关单元测试。
- [x] 5.3 运行 `ruff check .` 与 `black --check .`，或记录未运行原因。
