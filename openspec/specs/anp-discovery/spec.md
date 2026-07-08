# anp-discovery Specification

## Purpose

定义 `anp-agent` 插件当前对外发现能力：通过 `GET /agent/ad.json` 暴露 Agent Description，通过 `GET /agent/interface.json` 暴露 OpenRPC 接口文档，并保持与 ANP 官方 `RemoteAgent.discover()` 的直接发现流程兼容。

## Requirements

### Requirement: Agent Description 端点
插件 SHALL 暴露 `GET /agent/ad.json`，返回符合 ANP Agent Description 协议的 JSON 文档，使调用方能够发现该智能体；该文档 SHALL 保留当前直接发现兼容字段，并只声明当前真实支持且已启用的能力。Hermes tools 能力只有在 tool RPC 显式开启且存在 allowlisted 工具时才可声明。

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
- **THEN** 响应不得声明尚未实现的 Direct、Group、E2EE、DTR、Portal 或 Mediator 能力
- **AND** 当 tool RPC 未启用或没有 allowlisted 工具时，响应不得声明 Hermes tools 能力

#### Scenario: 声明已启用 Hermes tools 能力
- **WHEN** tool RPC 已启用且存在 allowlisted Hermes tools
- **THEN** `/agent/ad.json` 可以声明 Hermes tools 能力
- **AND** 声明内容 SHALL 指向 `/agent/interface.json` 中当前已暴露的 `hermes.tool.*` 方法

### Requirement: OpenRPC 接口端点
插件 SHALL 暴露 `GET /agent/interface.json`，返回描述可用 RPC 方法的 OpenRPC 文档。OpenRPC methods SHALL 始终包含当前基础方法，并在 tool RPC 启用时额外包含当前 allowlisted Hermes tools 对应的 `hermes.tool.*` 方法。

#### Scenario: 直接访问 interface.json
- **WHEN** 调用方 GET `/agent/interface.json`
- **THEN** 返回包含可用方法的 OpenRPC JSON 文档，且至少包含 `chat` 与 `anp.get_capabilities`

#### Scenario: chat 参数说明
- **WHEN** 调用方读取 OpenRPC 文档中的 `chat` 方法
- **THEN** 文档说明 `chat` 支持 legacy `params.message` 与 Core Binding `params.body.message`

#### Scenario: capabilities 方法说明
- **WHEN** 调用方读取 OpenRPC 文档
- **THEN** 文档包含 `anp.get_capabilities` 方法及其 capability negotiation 用途说明

#### Scenario: OpenRPC 声明 allowlisted 工具方法
- **WHEN** tool RPC 已启用且存在 allowlisted Hermes tool
- **THEN** OpenRPC methods 包含对应 `hermes.tool.<tool_name>` 方法
- **AND** 不包含未 allowlist、denylisted 或当前不可用的工具方法

#### Scenario: OpenRPC 不声明关闭的工具能力
- **WHEN** tool RPC 未启用
- **THEN** OpenRPC methods 不包含任何 `hermes.tool.*` 方法

### Requirement: 与 ANP demo 客户端兼容
生成的 `ad.json` 和 `interface.json` SHALL 能够被 ANP 官方 `RemoteAgent.discover()` 正确解析，并支持 `await agent.chat(...)` 形式的调用。

#### Scenario: RemoteAgent 发现
- **WHEN** ANP demo 客户端执行 `RemoteAgent.discover("http://host:port/agent/ad.json", auth)`
- **THEN** 发现成功，客户端可以调用智能体暴露的方法

### Requirement: DID 文档路径说明
插件文档 SHALL 按 DID WBA path DID 规则描述当前默认 DID 文档公开路径。对于包含 path segments 的 DID，例如 `did:wba:<host>:agent:e1_<fingerprint>`，文档 SHALL 说明 DID 文档路径为 `/agent/e1_<fingerprint>/did.json`，不得将 `/.well-known/did.json` 描述为当前默认 path DID 的公开路径。

#### Scenario: path DID 文档路径
- **WHEN** 插件生成的 DID 包含 `agent` 和 `e1_<fingerprint>` path segments
- **THEN** README、CLAUDE 与 OpenSpec 文档描述的 DID 文档路径为 `/agent/e1_<fingerprint>/did.json`

### Requirement: 当前发现能力边界
插件文档 SHALL 将 `GET /agent/ad.json`、`GET /agent/interface.json` 与 `GET /.well-known/agent-descriptions` 描述为当前已实现的发现入口，并明确 `/agent/ad.json` 是直接发现入口，`/.well-known/agent-descriptions` 是主动发现入口。

#### Scenario: 当前发现入口说明
- **WHEN** 用户阅读当前发现能力文档
- **THEN** 文档说明当前调用方可以使用 `/agent/ad.json` 作为直接发现入口，也可以使用 `/.well-known/agent-descriptions` 获取 agent descriptions collection

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
