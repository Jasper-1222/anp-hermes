## MODIFIED Requirements

### Requirement: Agent Description 端点
插件 SHALL 暴露 `GET /agent/ad.json`，返回符合 ANP Agent Description 协议的 JSON 文档，使调用方能够发现该智能体；该文档 SHALL 保留当前直接发现兼容字段，并只声明当前真实支持的能力。

#### Scenario: 直接访问 ad.json
- **WHEN** 调用方 GET `/agent/ad.json`
- **THEN** 返回包含智能体名称、描述、入口地址、服务 DID 和接口地址的 JSON 文档

#### Scenario: 保持直接发现兼容字段
- **WHEN** 调用方读取 `/agent/ad.json`
- **THEN** 响应继续包含 `id`、`name`、`description`、`endpoint` 和 `interfaces` 字段，且 `interfaces` 至少包含 OpenRPC interface URL

#### Scenario: 声明 ANP Agent Description 基础字段
- **WHEN** 调用方读取 `/agent/ad.json`
- **THEN** 响应包含 `protocolType: "ANP"`、`protocolVersion`、`type: "AgentDescription"`、`url`、`did`、`securityDefinitions` 和 `security` 字段

#### Scenario: 不声明未实现能力
- **WHEN** 调用方读取 `/agent/ad.json`
- **THEN** 响应不得声明尚未实现的 Direct、Group、E2EE、DTR、Portal、Mediator 或 Hermes tools 能力

### Requirement: 当前发现能力边界
插件文档 SHALL 将 `GET /agent/ad.json`、`GET /agent/interface.json` 与 `GET /.well-known/agent-descriptions` 描述为当前已实现的发现入口，并明确 `/agent/ad.json` 是直接发现入口，`/.well-known/agent-descriptions` 是主动发现入口。

#### Scenario: 当前发现入口说明
- **WHEN** 用户阅读当前发现能力文档
- **THEN** 文档说明当前调用方可以使用 `/agent/ad.json` 作为直接发现入口，也可以使用 `/.well-known/agent-descriptions` 获取 agent descriptions collection

## ADDED Requirements

### Requirement: Well-known Agent Descriptions 端点
插件 SHALL 暴露公开的 `GET /.well-known/agent-descriptions` 端点，返回包含当前 Hermes ANP 服务智能体索引项的 JSON-LD CollectionPage。

#### Scenario: 直接访问 well-known agent descriptions
- **WHEN** 调用方 GET `/.well-known/agent-descriptions`
- **THEN** HTTP 状态码为 200，响应体为 JSON-LD 对象，包含 `@context`，`@type` 为 `CollectionPage`，`url` 为当前 well-known URL，且包含 `items` 数组

#### Scenario: CollectionPage 包含当前服务智能体索引项
- **WHEN** 调用方读取 `/.well-known/agent-descriptions` 响应
- **THEN** `items` 数组包含且仅包含当前 Hermes ANP 服务智能体的索引项，且该 item 的 `@type` 为 `ad:AgentDescription`，`@id` 指向当前 `/agent/ad.json` URL，`name` 与 `/agent/ad.json` 一致，`did` 为当前服务 DID

#### Scenario: CollectionPage item 引用直接发现文档
- **WHEN** 调用方分别读取 `/.well-known/agent-descriptions` 与 `/agent/ad.json`
- **THEN** CollectionPage 中的 agent item 通过 `@id` 引用 `/agent/ad.json`，不要求内嵌完整 `description`、`endpoint` 或 `interfaces` 字段

#### Scenario: well-known 发现端点无需认证
- **WHEN** 调用方未携带 DID WBA HTTP Signature 访问 `/.well-known/agent-descriptions`
- **THEN** 插件仍返回公开发现文档，不进入 `/agent/rpc` 认证流程
