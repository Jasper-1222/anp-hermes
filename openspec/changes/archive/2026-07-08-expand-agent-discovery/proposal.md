## Why

当前 `GET /agent/ad.json` 已能支持本地 `RemoteAgent.discover()` 直接发现，但 Agent Description 字段仍偏最小，且缺少 ANP 主动发现入口 `GET /.well-known/agent-descriptions`。为提升与 ANP-07 / ANP-08 发现流程的互通性，需要在不破坏现有直接发现路径的前提下补齐标准发现面。

## What Changes

- 扩展 `GET /agent/ad.json` 返回的 Agent Description，保留现有 `id`、`name`、`description`、`endpoint`、`interfaces` 字段以维持 `RemoteAgent.discover()` 兼容。
- 新增 `GET /.well-known/agent-descriptions`，返回包含当前单个 Hermes ANP 服务智能体的 CollectionPage。
- CollectionPage 中复用与 `/agent/ad.json` 一致的 agent description，避免双份发现数据漂移。
- 更新文档与 OpenSpec：将 `/.well-known/agent-descriptions` 从“后续增强能力”提升为当前已实现发现入口。
- 增加 server/integration 测试，覆盖直接发现、well-known 发现、接口 URL、DID、OpenRPC 兼容字段。
- 不新增 DTR、Portal、Mediator、多 agent registry，也不改变 `/agent/rpc` 与 bridge 行为。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `anp-discovery`: 增加 well-known agent descriptions 发现入口，扩展 Agent Description 字段，并更新当前发现能力边界。

## Impact

- 代码：`plugins/anp-agent/server.py`，必要时增加构造 Agent Description / CollectionPage 的辅助函数。
- 测试：`plugins/anp-agent/tests/test_server.py`，必要时补充现有 integration/E2E 发现测试。
- 文档：根 README、插件 README、`docs/anp-hermes-openspec-execution-state.md` 中的当前发现能力说明。
- API 行为：新增公开 HTTP GET 端点 `/.well-known/agent-descriptions`；现有 `/agent/ad.json`、`/agent/interface.json`、`/agent/rpc` 保持兼容。
