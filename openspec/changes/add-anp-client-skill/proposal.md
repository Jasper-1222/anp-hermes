## Why

当前 Hermes `anp-agent` plugin 已让 Hermes 成为可通过 ANP DID WBA 认证和 JSON-RPC `chat` 调用的服务智能体，但调用方仍主要依赖仓库内测试脚本或手写 Python 客户端。为了形成端到端社区参考实现，需要提供一个可通过通用 skill 安装包分发的客户端 skill。该安装包可以来自 ClawHub、压缩包、skill 发布网站或 URL 下载，让 Hermes、OpenClaw、WorkBuddy 等个人智能体能够稳定发现并调用服务智能体。

## What Changes

- 新增自包含通用 `anp-client` skill，作为个人智能体调用 ANP 服务智能体的客户端能力。
- 新增命令式入口：`whoami`、`serve-did`、`discover`、`chat`。
- 首次使用时自动生成并复用个人智能体 caller DID WBA 身份，默认存放在 `~/.anp-client/`。
- 支持直接 URL 发现服务智能体的 `/agent/ad.json` 与 `/agent/interface.json`，并调用 `/agent/rpc` 的 `chat` 方法。
- 使用 DID WBA HTTP Message Signatures 对 JSON-RPC `chat` 请求签名。
- 在 `SKILL.md` 中定义自然语言触发方式，并用固定样例夹具验证自然语言请求可规范化为命令参数。
- 第一期明确不支持 `hermes.tool.*`、服务通讯录、AP2、E2EE、群聊或多轮 session 同步。

## Capabilities

### New Capabilities
- `anp-client-skill`: 定义个人智能体安装自包含 ANP 客户端 skill 后，自动管理 caller DID、发现服务智能体并通过 DID WBA 签名 JSON-RPC `chat` 发起对话的能力。

### Modified Capabilities

无。

## Impact

- 新增独立目录 `clients/anp-client/`，包含 `SKILL.md`、运行脚本、依赖说明和测试。
- 复用现有 `scripts/start_did_server.py`、`scripts/anp_chat_client.py`、`plugins/anp-agent/tests/helpers/signing.py` 的协议和签名经验，但不要求发布包依赖仓库外路径或软链接。
- 新增针对客户端 skill 的单元、集成和自然语言样例夹具测试。
- 新增或扩展基于现有 Hermes plugin E2E harness 的端到端验证，证明个人智能体可调用服务智能体。
- 不改变现有服务端 `anp-agent` plugin 的对外契约，除非实现阶段发现客户端所需行为与既有 specs 存在实际不一致。