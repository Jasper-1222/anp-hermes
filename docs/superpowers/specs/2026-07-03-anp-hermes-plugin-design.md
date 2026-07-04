# ANP Hermes 插件设计文档

**日期**：2026-07-03  
**主题**：create-anp-hermes-plugin  
**目标**：为 ANP 社区贡献一个高质量的 Hermes 接入参考实现，让 Hermes 智能体作为 ANP 服务智能体被其他智能体发现和调用。

---

## 1. 背景与目标

### 1.1 背景

ANP（Agent Network Protocol）定义了智能体之间的身份认证与通信协议。Hermes 是一个功能完整的智能体框架，拥有自己的 gateway、session、tool 和 LLM 编排能力，但当前缺少官方认可的 ANP 接入方式。

### 1.2 目标

- 开发一个 Hermes 平台插件 `anp-agent`，安装在 `~/.hermes/plugins/anp-agent/` 下。
- 插件自动生成并保管 ANP 原生 DID WBA 身份（`did:wba:`）。
- 插件对外暴露标准 ANP 端点：`/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`。
- 调用方通过 DID WBA HTTP Message Signatures 认证后，请求被桥接到 Hermes 内部消息处理流程。
- 代码结构清晰、测试完善，适合作为 ANP 社区参考实现。

### 1.3 非目标

- 不实现 AP2 支付协议。
- 不实现端到端加密（E2EE）。
- 不依赖 DTR、Portal、Mediator、OpenClaw 等外部基础设施。
- 不修改 Hermes 核心代码。

---

## 2. 系统边界

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ANP 客户端进程                               │
│  ┌─────────────────┐                                                │
│  │ ANP Demo Client │  例如：anp.openanp.RemoteAgent                  │
│  │                 │  持有调用方 DID 文档和私钥                       │
│  └────────┬────────┘                                                │
└───────────┬─────────────────────────────────────────────────────────┘
            │ HTTP + DID WBA HTTP Message Signatures
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Hermes Gateway 进程                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    ANP Platform Plugin                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐  │  │
│  │  │ aiohttp 服务 │  │ ANPBridge   │  │ ANPAdapter            │  │  │
│  │  │ /agent/*    │  │ Future 桥接  │  │ BasePlatformAdapter   │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └───────────┬───────────┘  │  │
│  │         │                │                      │              │  │
│  │         ▼                ▼                      ▼              │  │
│  │   HTTP 请求处理    请求-响应映射         Hermes 消息接口         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Hermes Gateway Runner / AI Agent                  │  │
│  │     (session 管理、tool 调用、LLM 推理、skills 编排)             │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

- **ANP 客户端进程** ↔ **Hermes Gateway 进程**：唯一外部网络边界，使用 HTTP + DID WBA 认证。
- **ANP Platform Plugin** ↔ **Hermes Gateway Runner**：同一进程内接口调用。
- **ANP 服务端 = ANP Platform Plugin**，寄生在 Hermes Gateway 中，不是独立进程。

---

## 3. 目录结构

```
plugins/anp-agent/
├── plugin.yaml          # Hermes 插件清单
├── pyproject.toml       # 依赖声明
├── adapter.py           # ANPAdapter（继承 BasePlatformAdapter）
├── bridge.py            # ANPBridge（Future 桥接 + TTL 清理）
├── identity.py          # DID WBA 生成、加载、持久化
├── server.py            # aiohttp 应用和路由处理器
└── tests/
    ├── test_identity.py
    ├── test_bridge.py
    └── test_server.py
```

### 3.1 模块职责

- `identity.py`：只关心 DID 文档和私钥，不知道 HTTP 或 Hermes。
- `server.py`：只关心 HTTP 路由和 ANP 协议，不知道 Hermes 内部细节。
- `bridge.py`：连接 server 和 adapter，管理请求-响应映射。
- `adapter.py`：连接 Hermes 和 bridge，实现 `BasePlatformAdapter` 接口。

---

## 4. 数据流

一个完整的 ANP 调用流程：

```
1. ANP demo 客户端
   ↓ GET /agent/ad.json
   ↓ GET /agent/interface.json
   ↓ POST /agent/rpc (带 DID WBA HTTP Signature)

2. aiohttp server (server.py)
   ↓ 验证 HTTP Signature
   ↓ 解析 JSON-RPC body
   ↓ 调用 bridge.call(rpc_id, method, params, caller_did)

3. ANPBridge (bridge.py)
   ↓ 创建 Future
   ↓ 构造 MessageEvent
   ↓ 调用 adapter.handle_message(event)

4. ANPAdapter (adapter.py)
   ↓ Hermes Gateway Runner 处理事件
   ↓ Hermes Agent Core 生成回复
   ↓ 调用 adapter.send(chat_id="anp:{rpc_id}", content=reply)

5. ANPBridge (bridge.py)
   ↓ 找到对应 Future，设置结果

6. aiohttp server
   ↓ 返回 JSON-RPC 2.0 响应
```

注意：Hermes 的 `handle_message()` 会快速返回，真正的回复通过 `send()` 回调回来，因此 Bridge 必须等待 Future。

---

## 5. 关键设计决策

### 5.1 依赖方案

- 插件核心使用 `anp>=0.8.8,<0.9.0`（不含 `[api]` extras），避免引入 FastAPI/OpenAI 与 Hermes 冲突。
- 端到端测试客户端单独使用 `anp[api]`。
- `~/agent-network-protocol` 源码仅用于调研，不作为项目依赖。

### 5.2 手动构建 ANP 端点

- 插件内部直接启动 aiohttp 服务器，手动实现 `/agent/ad.json`、`/agent/interface.json`、`/agent/rpc`。
- 不使用 `anp.openanp` 的 `@anp_agent` 装饰器，因为该装饰器假设服务是独立 FastAPI 应用，而我们需桥接到已运行的 Hermes Agent Core。

### 5.3 aiohttp 作为内置 HTTP 服务器

- 与 Hermes 的 `webhook.py` 平台适配器保持一致。
- 异步生命周期与 Hermes gateway 的 asyncio 主循环兼容。

### 5.4 asyncio Future 桥接请求-响应

- 收到 `/agent/rpc` 请求时创建 `asyncio.Future`。
- 通过 `handle_message(event)` 将事件交给 Hermes。
- Hermes 回复时调用 `send(chat_id, ...)`，插件根据 `chat_id` 前缀 `anp:` 找到对应 Future 并设置结果。
- Future 字典加入 TTL 和过期清理，防止内存泄漏。

### 5.5 DID WBA 身份存储

- DID 文档、私钥 PEM、`agent.json` 默认存放在 `~/.hermes/plugins/anp-agent/` 下。
- 私钥文件权限 `0o600`。
- 可通过 `ANP_DATA_DIR` 或 `config.yaml` 覆盖。

### 5.6 通用 chat 方法

- `interface.json` 中仅声明一个 `chat` 方法，参数为 `message: str`，返回 `response: str`。
- Hermes 的能力由内部 skills、tools、LLM 配置决定，不在 ANP 层静态暴露所有工具。

### 5.7 认证与授权

- 第一期仅做认证，不做授权。
- 任何持有有效 DID WBA 身份的调用方都可以调用。
- 测试环境需设置 `ANP_ALLOW_ALL_USERS=1` 以通过 Hermes 的 allowlist 检查。

---

## 6. 配置项

优先级：**环境变量 > config.yaml extra > 默认值**。

| 配置项 | 环境变量 | config.yaml 路径 | 默认值 | 说明 |
|---|---|---|---|---|
| 监听 host | `ANP_HOST` | `gateway.platforms.anp.extra.host` | `0.0.0.0` | HTTP 服务监听地址 |
| 监听 port | `ANP_PORT` | `gateway.platforms.anp.extra.port` | `8900` | HTTP 服务监听端口 |
| DID hostname | `ANP_HOSTNAME` | `gateway.platforms.anp.extra.hostname` | `localhost` | 生成 did:wba 时使用的 hostname |
| 公开 endpoint | `ANP_ENDPOINT` | `gateway.platforms.anp.extra.endpoint` | `http://{hostname}:{port}` | ad.json 中声明的服务地址 |
| 数据目录 | `ANP_DATA_DIR` | `gateway.platforms.anp.extra.data_dir` | `~/.hermes/plugins/anp-agent/` | DID 和私钥存储路径 |
| 请求超时 | `ANP_REQUEST_TIMEOUT` | `gateway.platforms.anp.extra.request_timeout` | `60` | 等待 Hermes 回复的最大秒数，默认保持较短以尽快失败 |
| Future TTL | `ANP_FUTURE_TTL` | `gateway.platforms.anp.extra.future_ttl` | `120` | pending future 过期清理时间，应略大于请求超时 |

---

## 7. 错误处理策略

| 层级 | 错误类型 | HTTP 状态码 | JSON-RPC error code |
|---|---|---|---|
| 协议层 | JSON 解析失败 | 400 | -32700 |
| 协议层 | 缺少 id/method | 400 | -32600 |
| 认证层 | DID WBA 签名无效 | 401 | -32001 |
| 认证层 | DID 无法解析 | 401 | -32002 |
| 应用层 | 方法不存在 | 200 | -32601 |
| 应用层 | 处理超时 / 内部错误 | 200 | -32603 |

---

## 8. 测试策略

### 8.1 单元测试

- `test_identity.py`：DID 生成、加载、私钥权限、覆盖写入。
- `test_bridge.py`：Future 创建/设置/超时、TTL 清理、重复 rpc_id 处理。
- `test_server.py`：HTTP 路由、JSON-RPC 解析、认证成功/失败、错误码。

### 8.2 集成测试

- 启动 aiohttp server + ANPBridge + mock adapter（不依赖完整 Hermes）。
- 使用 `anp.openanp.RemoteAgent` 或 `DIDWbaAuthHeader` 直接构造请求。
- 覆盖 discover → call 完整流程。

### 8.3 E2E 测试

- 启动完整 Hermes gateway（需要 LLM/工具配置）。
- 使用 ANP demo 客户端调用。
- CI 中可跳过，依赖外部 LLM 配置。

---

## 9. 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| DID WBA 认证依赖调用方持有有效 DID 文档 | 测试时使用 ANP SDK 自带示例 DID，文档说明如何生成测试身份 |
| 通用 `chat` 接口无法表达复杂工具调用 | 第一期聚焦基本对话；第二期评估将 Hermes tools 映射为 ANP 方法 |
| 插件与 Hermes 内部 API 耦合 | 仅使用公开/稳定的适配器接口，参考 Hermes 官方插件示例 |
| ANP SDK 版本升级导致接口变化 | 锁定主版本号 `anp>=0.8.8,<0.9.0`，CI 运行兼容性测试 |
| 依赖冲突 | 插件核心使用 `anp` 基础包，测试客户端使用 `anp[api]` |
| Gateway allowlist 默认拒绝新平台 | 在 `plugin.yaml` 中声明 `ANP_ALLOW_ALL_USERS`，README 说明测试环境需设置 |
| Future 残留导致内存泄漏 | 为 pending futures 设置 TTL，在 `call()` 入口清理过期项，在 `disconnect()` 中取消所有未完成 futures |

---

## 10. 部署步骤

1. 安装插件：`pip install -e plugins/anp-agent/` 或复制到 `~/.hermes/plugins/anp-agent/`。
2. 配置 `~/.hermes/config.yaml` 启用 `anp` 平台，设置 `host`/`port`/`hostname`。
3. 启动 Hermes gateway，插件自动生成 DID 并监听端口。
4. 使用 ANP demo 客户端调用 `RemoteAgent.discover(...)` 并发送 `chat` 请求。

---

## 11. 后续待办

- 调研 AP2 支付协议集成方案。
- 调研 E2EE 加密集成方案。
- 评估是否将 Hermes tools 动态映射为 ANP 方法。
