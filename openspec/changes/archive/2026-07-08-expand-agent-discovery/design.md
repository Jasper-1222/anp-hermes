## Context

当前插件已经提供两个公开发现端点：

- `GET /agent/ad.json`：返回最小 Agent Description，供当前 ANP SDK `RemoteAgent.discover()` 直接发现。
- `GET /agent/interface.json`：返回 OpenRPC 文档，声明 `chat` 与 `anp.get_capabilities`。

当前 `ad.json` 字段较少，但已经被本地 demo/E2E 依赖；因此本变更应采用“扩展而非替换”的方式。路线图中要求补齐 `GET /.well-known/agent-descriptions`，返回单 agent 的 CollectionPage，以提升与 ANP 主动发现流程的互通性。

## Goals / Non-Goals

**Goals:**

- 新增 `GET /.well-known/agent-descriptions` 公开端点。
- 返回只包含当前 Hermes ANP 服务智能体索引项的 JSON-LD CollectionPage。
- 扩展 Agent Description 的自描述字段，同时保持现有 `RemoteAgent.discover()` 兼容字段不变。
- 让 `/agent/ad.json` 和 well-known CollectionPage 复用同一份 agent description 构造逻辑。
- 更新 README / 插件 README 中的发现入口说明。
- 增加测试覆盖直接发现和 well-known 主动发现。

**Non-Goals:**

- 不引入 DTR、Portal、Mediator、OpenClaw 或外部 registry。
- 不支持多 agent registry。
- 不改变 DID WBA 认证、`/agent/rpc`、bridge 或 Core Binding 能力协商行为。
- 不暴露 Hermes tools/skills。
- 不实现发布索引、订阅、分页游标或远程目录同步。

## Decisions

### 1. well-known 端点返回单 agent CollectionPage

新增端点：

```text
GET /.well-known/agent-descriptions
```

响应采用单 agent JSON-LD collection 结构，核心字段：

```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "did": "https://w3id.org/did#",
    "ad": "https://agent-network-protocol.com/ad#"
  },
  "@type": "CollectionPage",
  "url": "{endpoint}/.well-known/agent-descriptions",
  "items": [
    {
      "@type": "ad:AgentDescription",
      "name": "Hermes ANP Agent",
      "@id": "{endpoint}/agent/ad.json",
      "did": "{identity.did}"
    }
  ]
}
```

`items` 中放 Agent Description 的索引项，而不是内嵌完整 `/agent/ad.json` 内容。

理由：当前插件只代表一个 Hermes ANP 服务智能体；引入多 agent registry 会增加配置、授权和生命周期复杂度，超出本变更范围。

备选方案：返回裸 Agent Description。该方案实现更简单，但无法表达“发现入口可返回多个 agent”的协议方向，也不符合路线图中 CollectionPage 的明确目标。

### 2. `/agent/ad.json` 与 CollectionPage item 共享核心来源但职责不同

`server.py` 当前已有 `_build_ad_json(config, identity)`。本变更继续以它作为完整 Agent Description 的单一来源，并新增轻量索引项构造逻辑：CollectionPage item 使用 `/agent/ad.json` 的 `name`、当前服务 DID 和 AD 文档 URL，但不复制完整 `description`、`endpoint`、`interfaces`。

理由：ANP-08 的 `/.well-known/agent-descriptions` 是发现索引，不是完整 AD 文档替代品；避免在 CollectionPage 中复制完整 AD，既贴近协议，也减少双份发现数据漂移。

### 3. Agent Description 只增加低风险自描述字段

在保留现有字段的前提下，优先增加 ANP-07 基础字段：

- `protocolType: "ANP"`
- `protocolVersion: "1.0.0"`
- `type: "AgentDescription"`
- `url: "{endpoint}/agent/ad.json"`
- `did: identity.did`
- `securityDefinitions` 与 `security`，声明 DID WBA 认证边界

同时继续保留当前兼容字段：`id`、`name`、`description`、`endpoint`、`interfaces`。

不得声明尚未实现的 Direct、Group、E2EE、Hermes tools、DTR/Portal/Mediator 能力。

理由：发现数据是客户端选择调用路径的依据，过度声明会导致标准客户端调用未实现能力。

### 4. well-known 端点保持公开，无认证要求

与 `/agent/ad.json` 和 `/agent/interface.json` 一样，`/.well-known/agent-descriptions` 是发现入口，不进入 DID WBA 认证链路。

理由：发现入口需要在认证前可读取；认证保护仍留在 `/agent/rpc`。

### 5. 不改变现有直接发现 URL

`/agent/ad.json` 继续保留，并仍是 README 中的直接发现入口。well-known 作为新增主动发现入口。

理由：保持当前 demo、E2E 与用户安装文档兼容。

## Risks / Trade-offs

- **CollectionPage 具体字段可能与未来 ANP SDK 期望存在差异。** → 本变更按 ANP-08 当前文档使用 JSON-LD `@context`、`@type`、`url`、`items` 与索引项 `@id`，并通过测试固定当前契约。
- **扩展 Agent Description 可能误导客户端认为支持更多能力。** → 只声明当前真实支持能力，不写 Direct/Group/E2EE 或 Hermes tools。
- **公开 well-known 端点增加可被扫描的信息面。** → 只公开已在 `/agent/ad.json` 公开的信息；不暴露密钥、token、运行态路径或用户配置。
- **双入口可能增加文档复杂度。** → 文档明确区分：`/agent/ad.json` 是直接发现入口，`/.well-known/agent-descriptions` 是主动发现入口。

## Migration Plan

1. 增加 server 测试，先覆盖 `GET /.well-known/agent-descriptions` 的 JSON-LD CollectionPage shape 和单 agent 索引项。
2. 扩展 `_build_ad_json()`，保留兼容字段。
3. 新增 `_build_agent_descriptions_collection()` 和对应 aiohttp handler。
4. 注册 well-known 路由。
5. 更新 README、插件 README、OpenSpec 执行状态文档中的发现入口说明。
6. 运行 targeted tests、OpenSpec validate、lint/format。

回滚策略：移除新增 route 和 collection 构造即可；现有 `/agent/ad.json` 直接发现路径不依赖 well-known 端点。

## Open Questions

无阻塞问题。CollectionPage 暂不实现分页；除 `@context`、`@type`、`url`、`items` 外是否增加 `totalItems` 等便利字段，可在实现时按最小兼容原则决定，并由测试固定。
