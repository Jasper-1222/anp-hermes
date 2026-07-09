# TODOS

> 注：已纳入本次实现计划的工作项不在此处重复跟踪。TODO-1（调研 anp SDK verifier 正确用法）已作为工程审查任务 T3 进入实施计划。

- **TODO-5: 支持个人智能体公开 DID 托管或 hostname 初始化**
  - 上下文：`add-anp-client-skill` 第一期默认生成 `did:wba:localhost...`，signed `chat` 只承诺同机 loopback 服务智能体；HTTPS endpoint 仅表示传输安全策略允许，远程服务通常无法解析本机 localhost DID。
  - 目标：设计 `anp-client` 的公开 DID 文档托管或显式 hostname 初始化能力，使个人智能体可被远程 HTTPS 服务智能体解析和认证。
  - 依赖：第一期 `clients/anp-client/` 自包含 skill、身份管理、`serve-did` 本地开发链路完成后再评估。

- **TODO-2: 支持 AP2 支付协议**
  - 上下文：设计文档 §11 后续待办；第一期明确排除。
  - 目标：调研 AP2 协议集成方案，评估如何在插件中暴露支付能力。

- **TODO-3: 支持端到端加密（E2EE）**
  - 上下文：设计文档 §11 后续待办；第一期明确排除。
  - 目标：调研 ANP E2EE 加密方案，评估在 Hermes 插件中的集成方式。

- **TODO-4: 评估将 Hermes tools 动态映射为 ANP 方法**
  - 上下文：设计文档 §11 后续待办。
  - 目标：评估是否以及如何把 Hermes 的 tools 动态暴露为 `interface.json` 中的 OpenRPC methods，而非仅提供通用 `chat` 方法。
