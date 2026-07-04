> 本文档是 OpenSpec 变更级别的精简摘要。完整设计（系统边界、数据流、配置表、错误码、测试策略）见：`/home/peter/anp-hermes/docs/superpowers/specs/2026-07-03-anp-hermes-plugin-design.md`。

## Context

ANP（Agent Network Protocol）提供了一套开放的智能体身份认证与通信协议。Hermes 是一个功能完整的智能体框架，但当前缺少官方认可的 ANP 接入方式。本项目旨在为 Hermes 开发一个 ANP 平台插件，使其能够作为 ANP 网络上的服务智能体被其他智能体发现和调用。

关键约束：
- 使用 ANP 原生 DID WBA 身份（`did:wba:`），不引入 `did:cn` 或其他 DID 方法。
- 不使用 DTR、Portal、Mediator、OpenClaw 等外部基础设施，仅依赖 ANP Python SDK 和 Hermes 插件机制。
- 插件必须零侵入 Hermes 核心代码，便于社区贡献和独立发布。
- 第一期仅实现身份认证 + JSON-RPC 调用，AP2 支付和 E2EE 加密延后。

## Goals / Non-Goals

**Goals:**
- 提供可安装的 Hermes 平台插件 `anp-agent`，支持通过 `~/.hermes/plugins/` 目录加载。
- 插件自动生成并保管 ANP DID WBA 身份。
- 插件对外暴露标准 ANP 端点：`/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`。
- 调用方通过 DID WBA HTTP Message Signatures 认证后，请求被桥接到 Hermes 内部消息处理流程。
- 使用 ANP 官方 demo 客户端完成端到端测试。
- 代码结构清晰、测试完善，适合作为 ANP 社区参考实现。

详细模块边界与数据流见完整设计文档 §2-§4。

**Non-Goals:**
- 不实现 AP2 支付协议。
- 不实现端到端加密（E2EE）。
- 不提供前端 Portal 或注册中心（DTR）。
- 不修改 Hermes 核心代码。
- 不直接复用 `internet-of-agent-testnet` 的代码或架构。

## Decisions

### 决策 1：核心依赖使用 `anp` 包，测试客户端使用 `anp[api]`

**选择**：插件核心通过 PyPI 安装 `anp`（不含 `[api]` extras），避免引入 FastAPI/OpenAI 与 Hermes 依赖冲突；端到端测试客户端单独使用 `anp[api]`。`~/agent-network-protocol` 源码仅用于调研，不作为项目依赖。

### 决策 2：基于 OpenANP 手动构建端点，而不是使用 `@anp_agent` 装饰器

插件内部直接启动 aiohttp 服务器，手动实现 `/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`，将请求桥接到已运行的 Hermes Agent Core。

### 决策 3：使用 aiohttp 作为插件内置 HTTP 服务器

与 Hermes 的 `webhook.py` 平台适配器保持一致，异步生命周期与 Hermes gateway 的 asyncio 主循环兼容。

### 决策 4：通过 asyncio Future 桥接请求-响应，并加入 TTL 清理

收到 `/agent/rpc` 请求时创建 `asyncio.Future`，通过 `handle_message(event)` 交给 Hermes；Hermes 回复时调用 `send(chat_id, ...)`，插件根据 `chat_id` 前缀 `anp:` 找到对应 Future 并设置结果。Future 字典加入 TTL 和过期清理，防止内存泄漏。

### 决策 5：身份数据默认存储在 `~/.hermes/plugins/anp-agent/`

DID 文档、私钥 PEM、`agent.json` 默认存放在 `~/.hermes/plugins/anp-agent/` 下，可通过 `ANP_DATA_DIR` 环境变量或 `config.yaml` 覆盖。私钥文件权限 `0o600`。

### 决策 6：仅暴露一个通用 `chat` 方法

`interface.json` 中仅声明一个 `chat` 方法，参数为 `message: str`，返回 `response: str`。Hermes 的能力由内部 skills、tools、LLM 配置决定，不在 ANP 层静态暴露所有工具。

### 决策 7：配置来源与关键配置项

配置优先级：**环境变量 > `config.yaml` extra > 默认值**。

| 配置项 | 环境变量 | config.yaml 路径 | 默认值 | 说明 |
|---|---|---|---|---|
| 监听 host | `ANP_HOST` | `gateway.platforms.anp.extra.host` | `0.0.0.0` | HTTP 服务监听地址 |
| 监听 port | `ANP_PORT` | `gateway.platforms.anp.extra.port` | `8900` | HTTP 服务监听端口 |
| DID hostname | `ANP_HOSTNAME` | `gateway.platforms.anp.extra.hostname` | `localhost` | 生成 did:wba 时使用的 hostname |
| 公开 endpoint | `ANP_ENDPOINT` | `gateway.platforms.anp.extra.endpoint` | `http://{hostname}:{port}` | ad.json 中声明的服务地址 |
| 数据目录 | `ANP_DATA_DIR` | `gateway.platforms.anp.extra.data_dir` | `~/.hermes/plugins/anp-agent/` | DID 和私钥存储路径 |
| 请求超时 | `ANP_REQUEST_TIMEOUT` | `gateway.platforms.anp.extra.request_timeout` | `60` | 等待 Hermes 回复的最大秒数，默认保持较短以尽快失败 |
| Future TTL | `ANP_FUTURE_TTL` | `gateway.platforms.anp.extra.future_ttl` | `120` | pending future 过期清理时间，应略大于请求超时 |

### 决策 8：仅认证，不授权

第一期只验证调用方 DID WBA 签名的有效性，不维护 allowlist/blocklist。任何有效 DID 都可以调用。测试环境需设置 `ANP_ALLOW_ALL_USERS=1` 以通过 Hermes 的 allowlist 检查。

### 决策 9：错误响应策略

认证失败返回 HTTP 401 + JSON-RPC error body；其他错误返回 HTTP 200 + JSON-RPC error。完整错误码表见完整设计文档 §7。

## Risks / Trade-offs

- **[Risk] DID WBA 认证依赖调用方持有有效 DID 文档** → **Mitigation**：测试时使用 ANP SDK 自带示例 DID，文档说明如何生成测试身份。
- **[Risk] 通用 `chat` 接口可能无法表达复杂工具调用** → **Mitigation**：第一期聚焦基本对话能力；第二期评估是否将 Hermes tools 映射为 ANP 方法。
- **[Risk] 插件与 Hermes 内部 API（`BasePlatformAdapter`、`MessageEvent`）耦合** → **Mitigation**：仅使用公开/稳定的适配器接口，参考 Hermes 官方插件示例。
- **[Risk] ANP SDK 版本升级导致接口变化** → **Mitigation**：锁定主版本号 `anp>=0.8.8,<0.9.0`，CI 中运行兼容性测试。
- **[Risk] 依赖冲突** → **Mitigation**：插件核心使用 `anp` 基础包，测试客户端使用 `anp[api]`，必要时隔离到独立 venv。
- **[Risk] Gateway allowlist 默认拒绝新平台** → **Mitigation**：在 `plugin.yaml` 中声明 `ANP_ALLOW_ALL_USERS` 为 optional env，并在 README 中说明测试环境必须设置该变量。
- **[Risk] Future 残留导致内存泄漏** → **Mitigation**：为 pending futures 设置 TTL，在 `call()` 入口清理过期项，并在 `disconnect()` 中取消所有未完成的 futures。
- **[Trade-off] 手动构建 OpenRPC 文档而非自动生成** → 牺牲了一部分自动化，换取对 Hermes 生命周期的完全控制。

## Deployment Steps

1. 安装插件：`pip install -e plugins/anp-agent/` 或复制到 `~/.hermes/plugins/anp-agent/`。
2. 配置 `~/.hermes/config.yaml` 启用 `anp` 平台，设置 `host`/`port`/`hostname`。
3. 启动 Hermes gateway，插件自动生成 DID 并监听端口。
4. 使用 ANP demo 客户端调用 `RemoteAgent.discover(...)` 并发送 `chat` 请求。

## Testing Strategy

- **单元测试**：`plugins/anp-agent/tests/`，覆盖 identity、bridge、server。
- **集成测试**：启动 aiohttp server + ANPBridge + mock adapter，使用 ANP SDK 客户端验证 discover → call。
- **E2E 测试**：启动完整 Hermes gateway + ANP 插件，使用 demo 客户端调用（CI 可跳过）。

## Open Questions / Follow-ups

1. 是否需要在 `ad.json` 中声明支持的 ANP 协议版本？（建议声明）
2. 是否支持多个 profile 同时运行多个 ANP 服务智能体？（建议第一期不支持）

后续待办：AP2 支付、E2EE 加密、Hermes tools 动态映射为 ANP 方法。详见完整设计文档 §11。
