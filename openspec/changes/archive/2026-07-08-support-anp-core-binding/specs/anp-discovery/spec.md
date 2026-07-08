## MODIFIED Requirements

### Requirement: OpenRPC 接口端点
插件 SHALL 暴露 `GET /agent/interface.json`，返回描述可用 RPC 方法的 OpenRPC 文档。

#### Scenario: 直接访问 interface.json
- **WHEN** 调用方 GET `/agent/interface.json`
- **THEN** 返回包含可用方法的 OpenRPC JSON 文档，且至少包含 `chat` 与 `anp.get_capabilities`

#### Scenario: chat 参数说明
- **WHEN** 调用方读取 OpenRPC 文档中的 `chat` 方法
- **THEN** 文档说明 `chat` 支持 legacy `params.message` 与 Core Binding `params.body.message`

#### Scenario: capabilities 方法说明
- **WHEN** 调用方读取 OpenRPC 文档
- **THEN** 文档包含 `anp.get_capabilities` 方法及其 capability negotiation 用途说明
