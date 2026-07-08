## 1. 发现端点测试

- [x] 1.1 在 `tests/test_server.py` 增加 `GET /.well-known/agent-descriptions` 返回 HTTP 200、JSON-LD `@context`、`@type: CollectionPage`、`url` 与 `items` 数组的测试。
- [x] 1.2 在 `tests/test_server.py` 增加 CollectionPage 仅包含当前服务智能体索引项的测试，覆盖 item `@type: ad:AgentDescription`、`@id` 指向 `/agent/ad.json`、`name` 与 ad.json 一致、`did` 等于当前 `ANPIdentity.did`。
- [x] 1.3 在 `tests/test_server.py` 增加 CollectionPage item 作为 `/agent/ad.json` 索引项的测试，确认不要求内嵌完整 `description`、`endpoint` 或 `interfaces` 字段。
- [x] 1.4 在 `tests/test_server.py` 增加 well-known 发现端点无需认证、不会调用 `mock_auth.authenticate` 的测试。
- [x] 1.5 在 `tests/test_server.py` 扩展 `/agent/ad.json` 测试，确认保留直接发现兼容字段、补充 ANP Agent Description 基础字段，且不声明未实现能力。

## 2. 服务端实现

- [x] 2.1 在 `server.py` 扩展 `_build_ad_json()`，保留现有兼容字段，补充 ANP Agent Description 基础字段，并只声明当前真实发现/调用能力。
- [x] 2.2 在 `server.py` 新增 CollectionPage 构造辅助函数，生成指向 `/agent/ad.json` 的轻量索引项，不内嵌完整 Agent Description。
- [x] 2.3 在 `server.py` 新增 `GET /.well-known/agent-descriptions` handler。
- [x] 2.4 在 `create_app()` 中注册 well-known 路由，保持 `/agent/ad.json`、`/agent/interface.json`、`/agent/rpc` 行为不变。

## 3. 文档更新

- [x] 3.1 更新根 `README.md`，说明 `/agent/ad.json` 为直接发现入口、`/.well-known/agent-descriptions` 为主动发现入口。
- [x] 3.2 更新 `plugins/anp-agent/README.md`，补充 well-known 发现端点和返回 CollectionPage 的说明。
- [x] 3.3 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `expand-agent-discovery` 为当前 active change 与计划状态。

## 4. 验证

- [x] 4.1 运行 `openspec validate expand-agent-discovery --strict` 并修正 delta specs 问题。
- [x] 4.2 运行 `python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v`。
- [x] 4.3 运行 `cd /home/peter/anp-hermes/plugins/anp-agent && ruff check . && black --check .`。
