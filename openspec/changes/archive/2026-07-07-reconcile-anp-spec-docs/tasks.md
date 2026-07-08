## 1. OpenSpec 主规格校准

- [x] 1.1 补全 `openspec/specs/anp-discovery/spec.md` 的 Purpose，说明当前覆盖 `/agent/ad.json`、`/agent/interface.json` 与直接发现兼容性。
- [x] 1.2 补全 `openspec/specs/anp-identity/spec.md` 的 Purpose，说明当前覆盖 DID WBA 身份生成、私钥本地保管与身份加载。
- [x] 1.3 补全 `openspec/specs/anp-rpc-bridge/spec.md` 的 Purpose，说明当前覆盖 JSON-RPC 接收、DID WBA 认证和 Hermes 消息桥接。
- [x] 1.4 补全 `openspec/specs/anp-platform-adapter/spec.md` 的 Purpose，说明当前覆盖 Hermes 插件注册、生命周期、配置和 send 桥接。
- [x] 1.5 将 `anp-rpc-bridge` 正常回复契约从裸字符串 `result` 修正为 `result.response` 对象形态。
- [x] 1.6 将 `anp-identity` 的持久化产物修正为 DID 文档与私钥 PEM，移除当前阶段对 `agent.json` 的强制要求。
- [x] 1.7 将 `anp-auth-error-classification` 中 `AuthenticationError` 的强制字段修正为 `status_code`、`rpc_code`、`message` 与 `headers`，不再强制要求 `cause`。
- [x] 1.8 在 `anp-discovery` 中补充 path DID 文档路径说明，并明确 `/.well-known/agent-descriptions` 属于后续增强。
- [x] 1.9 在 `anp-platform-adapter` 相关说明中移除对已归档 `create-anp-hermes-plugin` 作为当前变更的暗示。

## 2. 项目文档校准

- [x] 2.1 更新根目录 `README.md`，保持 OpenSpec 目录说明与当前 archive/changes 结构一致。
- [x] 2.2 更新 `CLAUDE.md` 中 OpenSpec 命令示例，避免指向已归档的 `create-anp-hermes-plugin` 作为当前变更。
- [x] 2.3 更新 `CLAUDE.md` 仓库结构示例，移除 `create-anp-hermes-plugin` 当前进行中目录描述。
- [x] 2.4 更新 `CLAUDE.md` 的 DID 文档解析说明，将当前 path DID 默认路径描述为 `/agent/e1_<fingerprint>/did.json`。
- [x] 2.5 更新 `plugins/anp-agent/README.md` 的 DID 文档解析说明，将 `/.well-known/did.json` 修正为 path DID 规则。
- [x] 2.6 在相关文档中明确 `Authentication-Info`、`anp.get_capabilities`、`/.well-known/agent-descriptions`、runtime secret hardening 属于后续 OpenSpec 变更，不属于当前已实现契约。

## 3. OpenSpec 变更目录卫生

- [x] 3.1 对比 `openspec/changes/anp-agent-dialog-install` 与 `openspec/changes/archive/2026-07-06-anp-agent-dialog-install`，确认 active 残留已归档且无额外内容。
- [x] 3.2 对比 `openspec/changes/anp-hermes-e2e-tests` 与 `openspec/changes/archive/2026-07-06-anp-hermes-e2e-tests`，确认 active 残留已归档且无额外内容。
- [x] 3.3 对比 `openspec/changes/refactor-anp-auth-error-handling` 与 `openspec/changes/archive/2026-07-06-refactor-anp-auth-error-handling`，确认 active 残留已归档且无额外内容。
- [x] 3.4 删除确认重复且已归档的 active 残留目录，使 `openspec/changes/` 只保留真正活跃的变更和 `archive/`。

## 4. 验证与状态更新

- [x] 4.1 运行 `openspec validate reconcile-anp-spec-docs --strict` 并修复所有校验问题。
- [x] 4.2 运行 `openspec list`，确认 active changes 只包含预期变更。
- [x] 4.3 运行 `openspec list --specs`，确认主 specs 可正常列出。
- [x] 4.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `reconcile-anp-spec-docs` 的完成情况、验证结果和下一步 change。
