## MODIFIED Requirements

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
