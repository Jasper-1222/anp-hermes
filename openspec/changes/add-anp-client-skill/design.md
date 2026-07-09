## Context

当前仓库已经提供 Hermes `anp-agent` 服务端 plugin：服务智能体可通过 `/agent/ad.json`、`/agent/interface.json` 公开发现，并通过 `/agent/rpc` 接收 DID WBA HTTP Signature 认证后的 JSON-RPC `chat` 调用。调用方能力目前主要存在于 `scripts/start_did_server.py`、`scripts/anp_chat_client.py` 和测试 helper 中，尚未形成可通过压缩包、skill 发布网站、URL 下载或 ClawHub 等来源安装，并供 Hermes/OpenClaw/WorkBuddy 等个人智能体复用的通用 skill。

本设计新增独立的自包含客户端 skill，把现有 Python 客户端原型产品化为 `clients/anp-client/`。术语上，安装该 skill 的调用方称为“个人智能体”，安装 Hermes plugin 并提供 ANP 服务的被调用方称为“服务智能体”。

## Goals / Non-Goals

**Goals:**

- 提供可通过压缩包、skill 发布网站、URL 下载或 ClawHub 等来源分发的 `anp-client` skill 目录，不依赖仓库外相对软链接或绝对路径。
- 为个人智能体提供命令式入口：`whoami`、`serve-did`、`discover`、`chat`。
- 首次使用时自动生成 caller DID WBA 身份，并在 `~/.anp-client/` 中复用。
- 通过直接 URL 发现服务智能体，并使用 DID WBA 签名 JSON-RPC legacy `params.message` 调用本机 loopback 服务智能体的 `chat`。HTTPS endpoint 在第一期仅表示传输安全策略允许；远程服务若无法解析默认 `did:wba:localhost...` caller DID，会认证失败。
- 在 `SKILL.md` 中说明自然语言触发方式，并通过固定样例夹具验证自然语言请求可规范化为命令参数。
- 保持实现可测试：单元测试、mock 集成测试，以及基于现有 Hermes plugin E2E harness 的端到端验证。

**Non-Goals:**

- 不调用或包装 `hermes.tool.*`。
- 不实现服务通讯录、注册中心、服务别名或多服务路由。
- 不实现 AP2 支付、E2EE、群聊、DTR、Portal、Mediator 或多轮 session 同步。
- 不自动发布 caller DID 文档到公网；生产托管只做文档说明。
- 不修改 Hermes 核心或现有服务端 plugin 对外契约。

## Decisions

### Decision 1: 使用 `clients/anp-client/` 作为独立自包含 skill 根目录

最终目录采用：

```text
clients/anp-client/
├── SKILL.md
├── README.md
├── requirements.txt
├── scripts/
│   ├── anp_client.py
│   ├── did_identity.py
│   ├── did_server.py
│   └── signing.py
└── tests/
    ├── test_identity.py
    ├── test_discovery.py
    ├── test_chat.py
    ├── test_cli.py
    └── test_natural_language_examples.py
```

理由：`clients/anp-client/` 明确区分客户端 skill 与现有服务端 plugin，便于社区理解“个人智能体调用服务智能体”的双角色模型。目录内包含真实脚本文件和依赖说明，不使用软链接，适合 ClawHub/OpenClaw/Hermes/WorkBuddy 复制安装。

备选方案是单个大脚本或正式 Python 包。单脚本初期更快但边界差；正式包长期更干净但第一版安装链路更重。分层脚本的自包含 skill 在 MVP 和后续演进之间更平衡。

### Decision 2: DID 身份默认存放在 `~/.anp-client/`

`did_identity.py` 负责创建和加载：

```text
~/.anp-client/did.json
~/.anp-client/private_key.pem
```

支持 `ANP_CLIENT_HOME` 覆盖以便测试和迁移。私钥权限必须为 `0600`。如果 `did.json` 或 `private_key.pem` 缺一、损坏或不匹配，客户端返回明确错误，不静默生成新 DID。

理由：`~/.anp-client/` 与具体宿主无关，适合通用个人智能体。静默重建身份会破坏服务端 allowlist、审计日志和用户对 DID 的认知，因此第一期选择显式失败。

### Decision 3: `serve-did` 只提供本地 loopback DID 文档服务

`anp_client.py serve-did` 默认监听 `127.0.0.1:18900`，按 DID WBA path DID 规则暴露：

```text
/agent/e1_<fingerprint>/did.json
```

命令输出本地服务智能体需要设置的：

```bash
ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

理由：本地 E2E 和开发需要服务智能体解析个人智能体 DID 文档；但面向公网的 DID 文档托管涉及域名、HTTPS、部署和信任边界，超出第一期范围。loopback 限制保持最小安全面。

### Decision 4: 第一版 chat 使用 legacy `params.message`

`chat` 构造当前服务端已稳定支持的 JSON-RPC 请求：

```json
{
  "jsonrpc": "2.0",
  "id": "chat-<uuid>",
  "method": "chat",
  "params": {"message": "..."}
}
```

使用 ANP SDK `DIDWbaAuthHeader` 对实际发送 body 生成 HTTP Message Signature。Core Binding `params.meta/body` 后续可增加，但不作为 MVP 默认。

理由：现有服务端、手写客户端和 E2E 已验证 legacy `params.message`，第一期目标是把链路产品化而不是引入协商复杂度。

### Decision 5: 命令式为稳定验收标准，自然语言通过夹具验证

`SKILL.md` 同时说明自然语言触发和命令式用法。测试不依赖具体宿主 LLM，而是维护固定自然语言样例夹具，验证这些表达可规范化为 `action`、`endpoint`/`ad_url`、`message` 等命令参数。

理由：用户体验需要自然语言；但 Hermes/OpenClaw/WorkBuddy 的模型解析可能存在差异。样例夹具让自然语言支持范围可审查、可回归，而命令式 CLI 保证跨宿主验收稳定。

### Decision 6: endpoint 安全策略采用严格 MVP

客户端只允许：

- loopback HTTP：`localhost`、`127.0.0.1`、`::1`
- HTTPS URL

非 loopback HTTP 默认拒绝。第一期不提供 `--allow-insecure-http`。

理由：本地 Hermes E2E 需要 HTTP loopback；生产和跨网络调用应使用 HTTPS。拒绝局域网/公网明文 HTTP 可以避免将测试便利误用为默认安全策略。

## Risks / Trade-offs

- **宿主 skill 规则差异** → 通过自包含目录、真实脚本文件、无软链接和命令式验收降低差异风险；自然语言只用夹具验证第一期支持范围。
- **用户未启动 DID 文档服务导致认证失败** → 将 `-32002` 等错误映射为明确提示，要求先运行 `serve-did` 并配置本地服务智能体 `ANP_DID_RESOLVER_BASE_URL`。
- **自动生成 DID 后用户误删部分身份文件** → 缺一或损坏时直接报错，避免静默换 DID；文档说明如何备份或重置。
- **legacy `params.message` 与未来 Core Binding 演进存在差距** → 第一版保留简单稳定路径；后续 change 可增加 Core Binding 默认化或自动回退策略。
- **不支持 tool RPC 降低能力展示范围** → 第一版聚焦安全的发现与对话；工具调用需要 caller DID 授权、参数 schema 和风险确认，单独设计更安全。
- **loopback-only `serve-did` 限制跨机器测试** → 第一版保持安全最小面；如确需局域网测试，后续通过显式开关和风险提示扩展。

## Migration Plan

该 change 只新增客户端 skill，不迁移现有服务端 plugin 数据或配置。实现完成后，用户可直接从 `clients/anp-client/` 安装或发布到 ClawHub。若需要回滚，删除 `clients/anp-client/` 及相关测试即可，不影响现有 Hermes `anp-agent` plugin。