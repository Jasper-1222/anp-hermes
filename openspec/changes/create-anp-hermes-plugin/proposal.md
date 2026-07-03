## Why

ANP（Agent Network Protocol）的目标是构建开放的智能体互联网络。Hermes 是一个活跃的智能体框架，但当前缺乏官方、高质量的 ANP 接入方式。为了让 Hermes 智能体能作为服务智能体加入 ANP 网络，并以最小依赖实现端到端可测试，需要开发一个 Hermes ANP 平台插件。该插件将作为 ANP 社区的参考实现之一，展示如何让现有智能体框架零侵入地接入 ANP 协议。

## What Changes

- 新建 Hermes 平台插件 `anp-agent`，安装在 `~/.hermes/plugins/anp-agent/` 下。
- 插件启动时自动生成并保管 ANP 原生 DID WBA 身份（`did:wba:`），私钥由插件本地持久化。
- 插件对外暴露标准 ANP 端点：
  - `GET /agent/ad.json` — Agent Description
  - `GET /agent/interface.json` — OpenRPC 接口描述
  - `POST /agent/rpc` — JSON-RPC 2.0 调用入口
- 调用方通过 DID WBA HTTP Message Signatures 进行身份认证；服务端验证签名后，将请求桥接到 Hermes 内部消息处理流程。
- Hermes 处理完成后，通过插件的 `send()` 机制将回复返回给调用方。
- 测试使用 ANP 官方 demo 客户端（`anp.openanp.RemoteAgent`），无需 DTR、Portal、Mediator 或 OpenClaw。
- AP2 支付与 E2EE 加密明确放到后续 todo，本期不实现。

## Capabilities

### New Capabilities

- `anp-identity`：DID WBA 身份的自动生成、持久化与加载，私钥由智能体自己保管。
- `anp-platform-adapter`：Hermes 平台插件的生命周期管理（connect / disconnect / send / get_chat_info），通过 `platform_registry` 自注册。
- `anp-rpc-bridge`：将 ANP JSON-RPC 2.0 请求转换为 Hermes `MessageEvent`，并将 Hermes 的文本回复封装为 JSON-RPC 响应。
- `anp-discovery`：自动生成并对外暴露 `ad.json` 与 `interface.json`，使 ANP demo 客户端可以发现并调用 Hermes 智能体。

### Modified Capabilities

- 无

## Impact

- 新增一个 Python 包（插件目录），核心依赖 `anp`（当前 PyPI 稳定版本 0.8.8），端到端测试客户端额外依赖 `anp[api]`。
- 需要符合 Hermes 插件契约：`plugin.yaml` + `adapter.py`，并通过 `ctx.register_platform()` 注册。
- Hermes 配置中新增 `anp` 平台配置项（监听 host/port、DID 存储路径等）。
- 测试方式变为：启动 Hermes gateway + ANP 插件 → 使用 ANP demo 客户端调用。
- 代码需保持高质量，便于后续贡献给 ANP 社区作为参考实现。
