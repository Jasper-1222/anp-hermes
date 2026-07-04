# anp-discovery Specification

## Purpose
TBD - created by archiving change create-anp-hermes-plugin. Update Purpose after archive.
## Requirements
### Requirement: Agent Description 端点
插件 SHALL 暴露 `GET /agent/ad.json`，返回符合 ANP Agent Description 协议的 JSON 文档，使调用方能够发现该智能体。

#### Scenario: 直接访问 ad.json
- **WHEN** 调用方 GET `/agent/ad.json`
- **THEN** 返回包含智能体名称、描述、入口地址和接口地址的 JSON 文档

### Requirement: OpenRPC 接口端点
插件 SHALL 暴露 `GET /agent/interface.json`，返回描述可用 RPC 方法的 OpenRPC 文档。

#### Scenario: 直接访问 interface.json
- **WHEN** 调用方 GET `/agent/interface.json`
- **THEN** 返回包含可用方法（至少一个通用 chat 方法）的 OpenRPC JSON 文档

### Requirement: 与 ANP demo 客户端兼容
生成的 `ad.json` 和 `interface.json` SHALL 能够被 ANP 官方 `RemoteAgent.discover()` 正确解析，并支持 `await agent.chat(...)` 形式的调用。

#### Scenario: RemoteAgent 发现
- **WHEN** ANP demo 客户端执行 `RemoteAgent.discover("http://host:port/agent/ad.json", auth)`
- **THEN** 发现成功，客户端可以调用智能体暴露的方法

