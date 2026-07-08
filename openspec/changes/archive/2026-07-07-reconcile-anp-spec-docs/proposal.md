## Why

当前 `anp-agent` 已完成 Hermes ↔ ANP 最小链路，但 OpenSpec 主规格、README、CLAUDE 与当前实现之间存在多处不一致，容易误导后续开发与社区审阅。需要先用一个只做规格/文档校准的变更，把当前已实现契约和后续待实现能力边界写清楚，再进入后续 P0 代码修复。

## What Changes

- 修正 DID 文档公开路径说明：当前默认 DID 为 path DID，实际公开路径是 `/{path...}/did.json`，例如 `/agent/e1_<fingerprint>/did.json`，不是裸域 DID 的 `/.well-known/did.json`。
- 将 JSON-RPC 正常响应契约统一为当前实现和 E2E 使用的 `result.response` 对象形态，避免继续描述为裸字符串 `result`。
- 明确当前身份持久化契约只要求 DID 文档和私钥 PEM；`agent.json` 不再作为当前已实现的强制产物。
- 将 `AuthenticationError.cause` 从当前强制契约中移除或降级为实现细节，避免主规格要求不存在的字段。
- 补全归档后仍为 `TBD` 的主规格 Purpose。
- 清理 OpenSpec 活跃变更区中已完成且已有 archive 副本的残留目录。
- 更新 README 与 CLAUDE 中过期的 OpenSpec 状态、仓库结构和 DID 解析说明。
- 不修改插件业务代码；`Authentication-Info`、RPC bridge hardening、runtime secret、防并发冲突等代码修复由后续独立变更处理。

## Capabilities

### New Capabilities

无。本变更只校准现有能力规格和项目文档，不引入新能力。

### Modified Capabilities

- `anp-discovery`: 补全 Purpose，明确当前发现端点范围，并修正 DID 文档路径说明；`/.well-known/agent-descriptions` 仍作为后续能力，不在本变更中实现。
- `anp-identity`: 补全 Purpose，并将当前身份持久化契约限定为 DID 文档与私钥 PEM；移除当前阶段对 `agent.json` 的强制要求。
- `anp-rpc-bridge`: 补全 Purpose，并将正常 JSON-RPC 响应契约修正为 `result.response` 对象形态。
- `anp-auth-error-classification`: 调整 `AuthenticationError` 结构要求，使其与当前实现一致，不再强制要求 `cause` 字段。
- `anp-platform-adapter`: 补全 Purpose，并保持认证失败 JSON-RPC 错误响应契约与当前认证错误分类一致。

## Impact

- 影响 OpenSpec 主规格：
  - `openspec/specs/anp-discovery/spec.md`
  - `openspec/specs/anp-identity/spec.md`
  - `openspec/specs/anp-rpc-bridge/spec.md`
  - `openspec/specs/anp-auth-error-classification/spec.md`
  - `openspec/specs/anp-platform-adapter/spec.md`
- 影响项目文档：
  - `README.md`
  - `CLAUDE.md`
  - `plugins/anp-agent/README.md`
  - `docs/anp-hermes-openspec-execution-state.md`
- 影响 OpenSpec 目录卫生：清理已归档变更在 `openspec/changes/` 活跃区的残留目录。
- 不影响运行时代码、外部 HTTP API 行为、依赖版本或测试逻辑。
