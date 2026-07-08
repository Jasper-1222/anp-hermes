# ANP Hermes 当前实现综合分析报告

日期：2026-07-07  
范围：`/home/peter/anp-hermes` 当前实现与 `/home/peter/agent-network-protocol` 本地 ANP 规范、SDK、示例对照  
方式：只读分析，未修改业务代码

## 1. 总体结论

当前项目已经完成了一个可运行的 **Hermes ↔ ANP 最小参考实现**：

- 通过 Hermes 插件机制零侵入注册 `anp` 平台。
- 自动生成和加载 DID WBA 身份。
- 暴露 ANP/OpenANP 风格端点：
  - `GET /agent/ad.json`
  - `GET /agent/interface.json`
  - `POST /agent/rpc`
  - path DID 文档端点，例如 `/agent/e1_xxx/did.json`
- 在 `/agent/rpc` 上执行 DID WBA HTTP Message Signatures 认证。
- 将 JSON-RPC `chat` 请求桥接到 Hermes `BasePlatformAdapter.handle_message()`。
- 通过 Hermes `send()` 回填 JSON-RPC 响应。

对当前本地 Python OpenANP SDK 的最小链路而言，项目基本兼容：

- `RemoteAgent.discover()` 可以理解当前 `ad.json` 和 OpenRPC interface。
- `ANPClient.call_jsonrpc()` 风格的普通 JSON-RPC 调用可以工作。
- DID WBA e1 身份生成和 HTTP Message Signatures 验证方向正确。

但如果目标是“贡献给 ANP 社区的高质量参考实现”，当前仍需要一轮系统性打磨。主要问题集中在：

1. **协议兼容性**：缺少 `Authentication-Info` 成功响应头、Agent Description 字段过简、缺少 `/.well-known/agent-descriptions`、缺少 `anp.get_capabilities`。
2. **并发与 JSON-RPC 语义**：pending future 只按 `rpc_id` 全局索引，数字 id 会导致回复无法匹配，bridge 超时被包装成成功 `result`。
3. **生产部署可靠性**：DID resolver 依赖 monkeypatch，运行态私钥可能落在源码目录，授权边界偏弱。
4. **需求/文档一致性**：OpenSpec、README、实现之间存在多处冲突。
5. **测试方案**：主流程覆盖较好，但 hermetic E2E、真实组合超时路径、协议边界、ANP token 流程仍有缺口。

---

## 2. 当前项目解决的问题

项目目标可以概括为：

> 通过 Hermes 平台插件机制，让 Hermes 智能体作为 ANP 网络中的标准服务智能体被发现、认证和调用。

整体链路：

```text
ANP Client / RemoteAgent
        │
        │ DID WBA + HTTP Message Signatures + JSON-RPC
        ▼
Hermes anp-agent plugin
        │
        │ MessageEvent / BasePlatformAdapter.handle_message()
        ▼
Hermes Agent Core / LLM / Skills / Tools
```

一期目标实际覆盖：

- ANP 原生 DID WBA 身份。
- DID WBA HTTP Message Signatures 认证。
- OpenANP 风格 Agent Description 与 OpenRPC interface。
- 单一 `chat` JSON-RPC 方法。
- Hermes 消息桥接。
- mock LLM 与真实 LLM E2E 验证。

一期明确不覆盖：

- AP2 支付。
- E2EE 加密。
- DTR、Portal、Mediator、OpenClaw 等外部基础设施。
- Hermes tools 动态映射为 ANP methods。

---

## 3. 当前实现架构

### 3.1 模块划分

| 文件 | 主要职责 |
|---|---|
| `plugins/anp-agent/__init__.py` | 插件入口，通过 `ctx.register_platform()` 注册 `anp` 平台 |
| `plugins/anp-agent/adapter.py` | Hermes 平台适配器生命周期、HTTP 服务启动/关闭、`send()` 回填 RPC future |
| `plugins/anp-agent/server.py` | aiohttp 路由、Agent Description、OpenRPC、JSON-RPC 解析与响应 |
| `plugins/anp-agent/bridge.py` | ANP JSON-RPC 到 Hermes `MessageEvent` 的异步桥接 |
| `plugins/anp-agent/auth.py` | DID WBA 认证、JWT token key、DID resolver wrapper |
| `plugins/anp-agent/identity.py` | DID WBA 身份生成、加载、持久化、损坏备份 |
| `plugins/anp-agent/config.py` | 从 Hermes platform config 和环境变量加载 ANP 配置 |
| `plugins/anp-agent/constants.py` | 默认配置常量 |

### 3.2 请求处理流程

1. Hermes 加载插件，执行 `register(ctx)`。
2. 插件注册 `ANPAdapter` 为 `anp` 平台。
3. `ANPAdapter.connect()`：
   - 加载配置。
   - 生成或加载 DID WBA 身份。
   - 初始化 `ANPAuth`。
   - 初始化 `ANPBridge`。
   - 启动 aiohttp server。
4. 外部客户端访问 `GET /agent/ad.json` 获取 Agent Description。
5. 客户端读取 `GET /agent/interface.json` 获取 OpenRPC。
6. 客户端签名调用 `POST /agent/rpc`。
7. `server.py` 解析 JSON-RPC、认证调用方、路由到 `chat`。
8. `ANPBridge.call()` 创建 pending future，构造 Hermes `MessageEvent`。
9. Hermes Agent Core 处理消息。
10. Hermes 调用 `ANPAdapter.send()`。
11. `send()` 从 `chat_id` 中解析 rpc id，回填 pending future。
12. `/agent/rpc` 返回 JSON-RPC `result.response`。

---

## 4. 当前实现优点

### 4.1 零侵入 Hermes 核心

插件通过 Hermes 插件机制注册平台，没有修改 Hermes 核心代码。这符合项目最重要的社区贡献约束。

### 4.2 模块边界清晰

身份、认证、HTTP、桥接、配置各自独立，便于测试和后续维护。

### 4.3 使用 ANP SDK 生成 DID WBA 身份

当前通过 ANP SDK 的 `create_did_wba_document()` 生成 e1 DID WBA 身份，路线正确。

### 4.4 path DID 文档路由方向正确

对于 `did:wba:localhost:agent:e1_xxx`，实现注册类似：

```text
/agent/e1_xxx/did.json
```

这符合 DID WBA path DID 解析规则。

### 4.5 主流程测试已具备

已有单元、集成、E2E 测试，并设置覆盖率门槛。项目已经超过“一次性 demo”的质量水平。

---

## 5. 需求分析层面问题

### P0：OpenSpec、README 与实现存在不一致

| 问题 | 当前情况 | 建议 |
|---|---|---|
| RPC result 形态 | `anp-rpc-bridge` spec 写 `result` 是字符串；实现和 E2E 使用 `result.response` | 统一为 `result.response` |
| DID 文档路径 | README/CLAUDE 写 `/.well-known/did.json`；实现是 path DID 路由 | 文档改为 path DID 规则 |
| `agent.json` | spec 要求写入；实现未体现 | 明确删除该需求或补实现 |
| `AuthenticationError.cause` | spec 要求；实现没有 | 实现或删 spec |
| OpenSpec 活跃变更 | 已完成/已归档变更仍留在 `openspec/changes/` | 清理活跃目录或重新归档 |
| specs Purpose | 多个主 specs 仍为 `TBD` | 补全 Purpose |

建议先做一次文档/规格整理，避免后续开发依据过期规格继续扩大偏差。

### P1：授权策略需要明确

当前需求中混合了三件事：

1. DID WBA 认证。
2. Hermes 平台 allowlist。
3. `ANP_ALLOW_ALL_USERS=1` 测试开关。

风险是部署者可能把 `ANP_ALLOW_ALL_USERS=1` 当作常规生产配置。生产环境下，这意味着任意拥有有效 DID WBA 签名的调用方都可能驱动 Hermes。

建议明确三种模式：

| 模式 | 建议行为 |
|---|---|
| 本地测试 | 允许 `ANP_ALLOW_ALL_USERS=1` |
| 私有部署 | 配置 `ANP_ALLOWED_USERS` |
| 公开服务 | 增加 scope、rate limit、audit log |

并将 `ANP_ALLOW_ALL_USERS` 从 required env 移到 optional env。

### P1：会话语义需要定稿

当前设计使用：

```text
chat_id = anp:{rpc_id}
```

但 JSON-RPC `id` 是客户端本地相关 ID，不应被当作服务端全局 request key 或会话 key。

建议区分：

- JSON-RPC id：只用于响应关联。
- 内部 request id：服务端生成，保证唯一。
- 会话 key：由 caller DID 和可选 client session id 决定。

---

## 6. 系统设计层面问题

### P0：pending future 不能只按 `rpc_id` 全局索引

当前 `_pending` 只用 `rpc_id` 作为 key。

风险：

- 不同 DID 调用方同时使用 `id: "1"` 会冲突。
- 恶意调用方可以占用常见 id，导致其他请求失败。
- JSON-RPC `id` 本来不是全局唯一。

建议至少使用：

```python
pending_key = (caller_did, canonical_rpc_id)
```

更稳妥的方案：

```python
internal_request_id = uuid
chat_id = f"anp:{internal_request_id}"
_pending[internal_request_id] = PendingRequest(
    caller_did=caller_did,
    original_rpc_id=original_rpc_id,
    future=future,
)
```

### P0：数字 JSON-RPC id 会导致回复无法匹配

如果客户端发送：

```json
{"jsonrpc": "2.0", "id": 1, "method": "chat", "params": {"message": "hi"}}
```

当前 pending key 是整数 `1`，但 Hermes 回复时从 `chat_id="anp:1"` 中解析出来的是字符串 `"1"`，导致找不到 pending future。

建议二选一：

1. 严格 ANP Core Binding：只接受非空字符串 id。
2. 兼容 JSON-RPC：内部 canonical 化为字符串，但响应保留原始 id。

面向 ANP，建议采用第一种：`id` 必须是非空字符串。

### P0：Bridge 超时和异常不应包装成成功 result

当前 `ANPBridge.call()` 在超时、取消、handler 异常时返回中文错误字符串，`server.py` 再包装成成功响应：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "response": "处理请求超时"
  },
  "id": "..."
}
```

这违反 JSON-RPC 错误语义，也与已有 spec 中“超时返回 JSON-RPC error”不一致。

建议：

- `ANPBridge.call()` 成功时只返回业务文本。
- 超时、取消、内部异常抛结构化异常。
- `server.py` 转换为 JSON-RPC error。

示例：

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Hermes response timed out"
  },
  "id": "..."
}
```

### P0：认证成功后缺少 `Authentication-Info`

ANP DID WBA 规范要求首次 HTTP Message Signature 认证成功后，服务端通过 `Authentication-Info` 返回 access token，客户端后续可使用 Bearer token。

当前 `ANPAuth.authenticate()` 丢弃 verifier 返回的 response headers，只返回 caller DID。

影响：

- 初次签名请求可成功。
- 客户端无法缓存 token。
- 后续请求只能继续全量签名。
- 严格实现可能认为服务端未完整实现 DID WBA 流程。

建议认证结果结构化：

```python
@dataclass
class AuthResult:
    caller_did: str
    response_headers: dict[str, str]
```

然后 `/agent/rpc` 成功响应附加 `Authentication-Info`。

### P1：缺少 ANP-08 主动发现入口

当前只支持已知 URL 发现：

```text
/agent/ad.json
```

建议新增：

```text
GET /.well-known/agent-descriptions
```

返回最小 CollectionPage：

```json
{
  "type": "CollectionPage",
  "items": [
    {
      "type": "AgentDescription",
      "url": "http://localhost:8900/agent/ad.json"
    }
  ]
}
```

### P1：Agent Description 字段过简

当前 `/agent/ad.json` 足够让本地 `RemoteAgent.discover()` 工作，但不够贴近 ANP-07。

建议在保持现有兼容字段的基础上增加：

```json
{
  "protocolType": "ANP",
  "protocolVersion": "1.0.0",
  "type": "AgentDescription",
  "url": "http://.../agent/ad.json",
  "did": "did:wba:...",
  "identifier": "did:wba:...",
  "id": "did:wba:...",
  "name": "...",
  "description": "...",
  "securityDefinitions": {},
  "security": [],
  "interfaces": []
}
```

建议同时保留 `did`、`identifier`、`id`，兼容规范正文、OpenANP autogen 和当前实现。

### P1：缺少 `anp.get_capabilities`

ANP Core Binding 要求 endpoint 暴露：

```text
anp.get_capabilities
```

建议最小返回：

```json
{
  "service_did": "did:wba:...",
  "supported_profiles": ["openanp-chat"],
  "supported_security_profiles": ["did-wba-http-signature"],
  "methods": ["chat", "anp.get_capabilities"],
  "limits": {
    "max_request_bytes": 1048576,
    "timeout_seconds": 60
  }
}
```

---

## 7. 技术实现层面问题

### P0：运行态私钥和 DID 文件不应留在源码目录

当前工作区存在未跟踪运行态文件：

```text
plugins/anp-agent/did.json
plugins/anp-agent/private_key.pem
plugins/anp-agent/jwt_private_key.pem
plugins/anp-agent/jwt_public_key.pem
```

虽然当前未被 git 跟踪，但 `.gitignore` 没有明确忽略它们，存在误提交风险。

建议立即加入 `.gitignore`：

```gitignore
plugins/anp-agent/*.pem
plugins/anp-agent/did.json
plugins/anp-agent/*.did.json
```

更理想的是默认 `data_dir` 不指向插件源码目录，而是运行态数据目录，例如：

```text
~/.hermes/plugins/anp-agent/data/
```

或：

```text
~/.local/share/hermes/anp-agent/
```

### P0：`sys.path.insert(0, plugin_dir)` 有模块污染风险

当前插件入口将插件目录插入 `sys.path[0]`，内部使用 `from config import ...`、`from auth import ...` 等通用模块名。

风险：

- 其他插件或 Hermes 代码 `import config` 时可能误导入 ANP 插件模块。
- 多插件环境中可能出现不可预测冲突。

建议包化插件：

```text
plugins/anp-agent/anp_agent/
  __init__.py
  adapter.py
  server.py
  bridge.py
  auth.py
  identity.py
```

并使用相对导入：

```python
from .config import ANPConfig
```

### P0：DID resolver monkeypatch 不适合生产级实现

当前 `auth.py` monkeypatch ANP SDK 的 `resolve_did_wba_document`，并通过全局配置控制 resolver 行为。

风险：

- 同进程多个 `ANPAuth` 实例互相覆盖配置。
- 影响进程内其他 ANP SDK 使用者。
- `ANP_DID_RESOLVER_BASE_URL` override 时可能关闭 SSL 校验。

建议：

1. 短期限制 `ANP_DID_RESOLVER_BASE_URL` 只用于测试/开发。
2. 只对 `http://localhost` 允许关闭 SSL。
3. 中期向 ANP SDK 上游贡献 resolver injection 能力。

### P1：配置校验不足

建议增加配置范围和一致性校验：

| 配置 | 建议校验 |
|---|---|
| `port` | `0 <= port <= 65535` |
| `request_timeout` | `> 0` |
| `future_ttl` | `>= request_timeout` |
| `endpoint` | 合法 URL |
| `hostname` | 生产环境不应是 IP；测试可允许 localhost |
| `data_dir` | 不应默认指向源码目录 |

特别是 `future_ttl < request_timeout` 会导致 pending future 先被清理，外层请求仍在等待，行为会很难诊断。

### P1：DID 身份加载校验不足

当前加载时主要校验结构和 hostname。建议增强：

- 验证 DID document proof。
- 验证私钥与 DID 文档 public key 匹配。
- endpoint/serviceEndpoint 变化时明确更新或重新生成 DID 文档。
- 多进程共享 data_dir 时增加文件锁。

### P1：JSON-RPC 校验不完整

建议补充：

- `jsonrpc == "2.0"`。
- `id` 必须非空字符串。
- `params` 必须 object。
- `params.message` 必须存在且为字符串。
- batch request 明确拒绝。
- notification 是否支持要明确。
- 兼容 ANP Core Binding 的 `params.meta/body`。

### P1：`supports_async_delivery` 应显式为 False

ANP 当前 JSON-RPC 是短连接请求-响应模型，只有 pending future 存在时才能回填。请求结束后无法异步主动推送给客户端。

建议在 `ANPAdapter` 上显式设置：

```python
supports_async_delivery = False
```

---

## 8. 测试方案分析

### 8.1 当前已覆盖内容

当前测试体系已经覆盖：

- 配置加载。
- DID 身份生成/加载。
- DID WBA 认证错误映射。
- JSON-RPC HTTP 主流程。
- Bridge pending/future 管理。
- Adapter 生命周期。
- aiohttp + auth + bridge 集成测试。
- mock LLM echo E2E。
- 真实 LLM smoke / 多轮上下文 E2E。
- 覆盖率门槛。

### 8.2 P0：coverage 统计需要确认 source

当前 coverage 可能把测试文件计入 source，85% 门槛不一定真实代表业务代码覆盖率。

建议包化后配置：

```toml
[tool.coverage.run]
source = ["anp_agent"]
omit = [
  "tests/*",
  "*/tests/*",
]
```

### 8.3 P0：补真实 Bridge 超时集成测试

当前测试 mock 了 `bridge.call` 抛 `asyncio.TimeoutError`，但真实 `ANPBridge.call()` 自己捕获超时并返回字符串，所以没有覆盖真实组合行为。

建议新增测试：

- 使用真实 `ANPBridge`。
- `handle_message()` 不回填结果。
- 等待超时。
- 断言 `/agent/rpc` 返回 JSON-RPC error，而不是 `result.response`。

### 8.4 P1：mock E2E 应 hermetic

当前 mock LLM E2E 仍依赖真实：

```text
~/.hermes/config.yaml
```

建议 E2E 使用临时 HOME 或临时 Hermes config，将 provider、plugin、gateway 配置全部写入临时目录，避免本机配置污染测试结果。

### 8.5 P1：真实 LLM slow skip 应提前

真实 LLM 测试的 skip 应尽量发生在 fixture 初始化前，避免未启用 slow 测试时仍启动重资源。

建议使用 module-level marker 或 fixture-level skip。

### 8.6 P1：建议新增测试清单

协议边界：

1. `jsonrpc` 缺失或不是 `"2.0"`。
2. `id` 是数字。
3. `id` 是空字符串。
4. `params` 不是 object。
5. `params.message` 缺失。
6. `params.message` 非字符串。
7. batch request。
8. 超过 1MB 请求体。

并发与隔离：

1. 不同 caller DID 使用相同 id。
2. 同 caller 并发多个 id。
3. pending 上限触发。
4. future TTL 与 request timeout 的边界。

ANP 兼容：

1. `RemoteAgent.discover()` 真实 discover。
2. `ANPClient.call_jsonrpc()` 真实调用。
3. 成功认证响应包含 `Authentication-Info`。
4. Bearer token 后续请求可通过。
5. `/.well-known/agent-descriptions` 可发现。
6. `anp.get_capabilities` 返回最小 schema。

---

## 9. ANP 兼容性专项分析

### 9.1 已兼容内容

当前实现与本地 ANP 资料一致的部分：

- 三个核心端点与 OpenANP 示例一致：
  - `/agent/ad.json`
  - `/agent/interface.json`
  - `/agent/rpc`
- `RemoteAgent.discover()` 能读取当前 AD 与 OpenRPC。
- 普通 JSON-RPC 调用流程兼容 SDK 客户端。
- DID WBA e1 身份生成方向正确。
- HTTP Message Signatures 认证方向正确。
- path DID 文档路由符合 DID WBA path DID 解析规则。

### 9.2 主要兼容风险

| 优先级 | 问题 | 影响 |
|---|---|---|
| P0 | 成功认证后未返回 `Authentication-Info` | 客户端无法缓存 Bearer token |
| P0 | 生产 DID 解析依赖 monkeypatch / resolver override | 社区部署和多实例隔离风险 |
| P1 | Agent Description 字段过简 | 搜索、目录、非 Python SDK 互通风险 |
| P1 | 缺少 `/.well-known/agent-descriptions` | 只知道域名时无法主动发现 |
| P1 | 缺少 `anp.get_capabilities` | 不符合 Core Binding 能力发现要求 |
| P1 | RPC payload 未兼容 `params.meta/body` | Core Binding 兼容性不足 |
| P2 | 只暴露 `chat` 方法 | 结构化服务能力弱 |
| P2 | 授权、限流、审计不足 | 生产公开部署风险 |

### 9.3 应优先参考的 ANP 本地文件

- `/home/peter/agent-network-protocol/AgentNetworkProtocol/03-did-wba-method-design-specification.md`
  - DID WBA、HTTP Message Signatures、`Authentication-Info`、Bearer token、认证与授权边界。
- `/home/peter/agent-network-protocol/AgentNetworkProtocol/07-anp-agent-description-protocol-specification.md`
  - Agent Description 字段和 interface 结构。
- `/home/peter/agent-network-protocol/AgentNetworkProtocol/08-ANP-Agent-Discovery-Protocol-Specification.md`
  - `/.well-known/agent-descriptions` 主动发现。
- `/home/peter/agent-network-protocol/AgentNetworkProtocol/message/01-core-binding.md`
  - JSON-RPC 2.0、`params.meta/auth/body`、`anp.get_capabilities`。
- `/home/peter/agent-network-protocol/anp/anp/openanp/client/agent.py`
  - `RemoteAgent.discover()` 实际行为。
- `/home/peter/agent-network-protocol/anp/anp/openanp/client/openrpc.py`
  - AD interfaces 与 OpenRPC 解析。
- `/home/peter/agent-network-protocol/anp/anp/authentication/did_wba_verifier.py`
  - verifier 成功响应 headers 与 token 流程。
- `/home/peter/agent-network-protocol/anp/anp/openanp/middleware.py`
  - 成功认证后写回 response headers 的参考实现。

---

## 10. 建议优化路线图

### 第一轮：P0 hardening

建议开一个 OpenSpec 变更，例如：

```text
hardening-anp-core-compatibility
```

范围：

1. 返回 DID WBA 成功认证的 `Authentication-Info`。
2. 修复 Bridge 超时/异常被包装成成功 result。
3. 修复 pending 只按 `rpc_id` 全局索引的问题。
4. 明确并校验 JSON-RPC `id` 语义。
5. 将运行态私钥和 DID 文件加入 `.gitignore`。
6. 修正 README/CLAUDE 中 DID 文档路径说明。
7. 补真实 Bridge 超时集成测试。

### 第二轮：ANP 社区互通增强

范围：

1. 扩展 Agent Description 到 ANP-07 友好形态。
2. 新增 `/.well-known/agent-descriptions`。
3. 新增 `anp.get_capabilities`。
4. 兼容 `params.meta/body`。
5. 补 ANP SDK discover/call/token 测试。

### 第三轮：工程化与发布质量

范围：

1. 包化插件，消除 `sys.path` 污染。
2. data_dir 与源码目录分离。
3. release zip 构建流程。
4. CI secret scan。
5. hermetic E2E。
6. coverage source 修正。

### 第四轮：能力增强

范围：

1. Hermes tools 动态暴露为 OpenRPC methods。
2. DID allowlist / scope / rate limit。
3. audit log。
4. production deployment 文档。
5. 后续 AP2 / E2EE。

---

## 11. Top 10 优先建议

1. **返回 DID WBA 成功认证的 `Authentication-Info`。**
2. **修复 Bridge 超时/异常被包装成成功 result。**
3. **修复 pending 只按 `rpc_id` 全局索引的问题。**
4. **明确并校验 JSON-RPC `id` 语义，避免数字 id bug。**
5. **把运行态私钥和 DID 文件加入 `.gitignore`，避免误提交。**
6. **修正 README/CLAUDE 中 DID 文档路径说明。**
7. **清理 OpenSpec 活跃/归档状态和主 specs 的 `TBD`。**
8. **扩展 Agent Description 字段，兼容 ANP-07。**
9. **新增 `/.well-known/agent-descriptions`。**
10. **新增 `anp.get_capabilities`。**

---

## 12. 最终评价

当前项目不是方向错误，而是已经从“能跑通”进入“需要打磨成社区级参考实现”的阶段。

最值得肯定的是：

- 架构方向正确。
- 零侵入 Hermes 核心。
- 最小 ANP/OpenANP 链路已打通。
- 测试体系已有基础。

最需要优先解决的是：

- 协议契约完整性。
- JSON-RPC 与 pending 并发正确性。
- DID WBA 成功认证 token 流程。
- 文档/规格/实现一致性。
- 私钥运行态文件安全。

建议下一步不要直接大规模重构，而是先开一个聚焦 P0 的 OpenSpec 变更，以小步方式把正确性和协议契约补齐。之后再做 ANP-07/08/Core Binding 兼容增强和插件工程化重构。
