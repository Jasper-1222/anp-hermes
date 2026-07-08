## ADDED Requirements

### Requirement: DID 文档路径说明
插件文档 SHALL 按 DID WBA path DID 规则描述当前默认 DID 文档公开路径。对于包含 path segments 的 DID，例如 `did:wba:<host>:agent:e1_<fingerprint>`，文档 SHALL 说明 DID 文档路径为 `/agent/e1_<fingerprint>/did.json`，不得将 `/.well-known/did.json` 描述为当前默认 path DID 的公开路径。

#### Scenario: path DID 文档路径
- **WHEN** 插件生成的 DID 包含 `agent` 和 `e1_<fingerprint>` path segments
- **THEN** README、CLAUDE 与 OpenSpec 文档描述的 DID 文档路径为 `/agent/e1_<fingerprint>/did.json`

### Requirement: 当前发现能力边界
插件文档 SHALL 将 `GET /agent/ad.json` 与 `GET /agent/interface.json` 描述为当前已实现的发现入口，并将 `/.well-known/agent-descriptions` 标记为后续增强能力而非当前实现。

#### Scenario: 当前发现入口说明
- **WHEN** 用户阅读当前发现能力文档
- **THEN** 文档说明当前调用方应使用 `/agent/ad.json` 作为直接发现入口
