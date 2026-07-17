# ANP Hermes 社区 Demo 演练脚本

本文档提供一步一步的 Live Demo 操作指南，帮助社区成员完整体验从身份创建、服务发现、DID WBA 认证到 JSON-RPC 调用的全链路。

每步包含三个要素：**可执行命令**、**预期终端输出**和**设计原理说明**。

## 前置条件

### 环境要求

- Python 3.10+
- Hermes Agent Runtime 已安装（`hermes gateway run` 可用）
- Linux 或 macOS（WSL2 可用）

### 依赖安装

```bash
# 克隆仓库
git clone https://github.com/Jasper-1222/anp-hermes.git
cd anp-hermes

# 安装插件（可编辑模式）
python3 -m pip install -e plugins/anp-agent[test,dev]

# 安装 ANP 调用端依赖
python3 -m pip install -r clients/anp-client/requirements.txt
```

### 配置检查

```bash
# 确认 Hermes 配置文件存在
cat ~/.hermes/config.yaml

# 确认 Hermes 可执行
which hermes
```

---

## Happy Path：完整调用链路（6 步）

---

### Step 1：创建调用方身份

每条 ANP 链路上的调用方都需要一个 DID WBA 身份。`anp-client whoami` 自动检查或创建本地身份。

**命令**：

```bash
python3 clients/anp-client/scripts/anp_client.py whoami
```

**预期输出**（首次运行时自动创建身份）：

```
个人智能体身份:
  DID: did:wba:localhost:agent:e1_B8xK2mP9vR4q
  私钥: /home/user/.anp-client/private_key.pem
  DID 文档: /home/user/.anp-client/did.json
```

第二次运行返回相同身份（从文件加载，不重新生成）。

> **设计原理**：为什么用 `did:wba:` 而非 `did:web:`？WBA（Web-Based Agent）是 ANP 社区为智能体场景设计的 DID 方法，原生支持 Ed25519 proof。DID 格式为 `did:wba:{hostname}:agent:e1_{fingerprint}`，其中 `fingerprint` 从 Ed25519 公钥的 multibase 编码派生。私钥以 `0o600` 权限存储在 `~/.anp-client/` 下，与 Hermes 服务端身份存储路径 `~/.hermes/data/anp-agent/` 隔离。

---

### Step 2：启动本地 DID 文档服务

DID WBA 签名验证需要调用方 DID 文档。在本地测试环境中，我们通过 `anp-client serve-did` 在 loopback 上提供调用方 DID 文档，方便服务端解析。

**命令**：

```bash
python3 clients/anp-client/scripts/anp_client.py serve-did --port 18900 &
```

**预期输出**：

```
DID 文档服务已启动: http://127.0.0.1:18900
DID: did:wba:localhost:agent:e1_B8xK2mP9vR4q
DID 文档路径: /agent/e1_B8xK2mP9vR4q/did.json
```

验证 DID 文档可访问：

```bash
curl -s http://127.0.0.1:18900/agent/e1_B8xK2mP9vR4q/did.json | python3 -m json.tool
```

**预期输出**（DID 文档结构）：

```json
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:wba:localhost:agent:e1_B8xK2mP9vR4q",
  "verificationMethod": [
    {
      "id": "did:wba:localhost:agent:e1_B8xK2mP9vR4q#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:wba:localhost:agent:e1_B8xK2mP9vR4q",
      "publicKeyMultibase": "z..."
    }
  ],
  "authentication": ["did:wba:localhost:agent:e1_B8xK2mP9vR4q#key-1"],
  "assertionMethod": ["did:wba:localhost:agent:e1_B8xK2mP9vR4q#key-1"]
}
```

> **设计原理**：DID WBA 解析默认通过 HTTPS `{hostname}/.well-known/did.json` 路径获取 DID 文档。本地测试中，`localhost` 没有公共 DNS，所以通过 `ANP_DID_RESOLVER_BASE_URL` 指向本地 DID 文档服务。该覆盖仅接受 loopback 地址，生产环境不依赖此机制。

---

### Step 3：配置并启动 Hermes ANP 插件

将 anp-agent 插件注册到 Hermes，并配置测试环境变量。

**配置 `~/.hermes/config.yaml`**（在现有 `gateway.platforms` 下添加）：

```yaml
gateway:
  platforms:
    anp:
      enabled: true
      extra:
        hostname: localhost
        port: 8900
```

**设置环境变量并启动**：

```bash
# 测试环境：允许所有调用方 + 指向本地 DID 解析
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900

# 启动 Hermes gateway（新终端或后台运行）
hermes gateway run --accept-hooks &
```

**验证服务端已启动**：

```bash
curl -s http://127.0.0.1:8900/agent/ad.json | python3 -m json.tool
```

**预期输出**：

```json
{
  "protocolType": "ANP",
  "protocolVersion": "1.0.0",
  "type": "AgentDescription",
  "url": "http://localhost:8900/agent/ad.json",
  "name": "Hermes ANP Agent",
  "description": "基于 Hermes 的 ANP 服务智能体参考实现，支持 chat 方法。",
  "endpoint": "http://localhost:8900",
  "id": "did:wba:localhost:agent:e1_XyZ789AbC",
  "did": "did:wba:localhost:agent:e1_XyZ789AbC",
  "securityDefinitions": {
    "didwba_sc": {
      "scheme": "didwba",
      "in": "header",
      "name": "Authorization"
    }
  },
  "security": "didwba_sc",
  "interfaces": [
    {
      "type": "openrpc",
      "url": "http://localhost:8900/agent/interface.json"
    }
  ]
}
```

> **设计原理**：
> - `securityDefinitions.didwba_sc` 声明了 DID WBA 自我认证方案，调用方须用 HTTP Message Signatures 签署请求
> - `security: "didwba_sc"` 表示这是全局安全方案，所有 `/agent/rpc` 调用都需要 DID WBA 签名
> - `ANP_ALLOW_ALL_USERS=1` 跳过调用方 DID 白名单校验，仅用于本地测试
> - Agent Description 的 `id` 字段使用与 `did` 相同的 DID WBA 标识符

---

### Step 4：发现服务智能体

使用 `anp-client discover` 获取服务智能体的元信息和可用方法列表。

**命令**：

```bash
python3 clients/anp-client/scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
```

**预期输出**：

```
服务智能体: Hermes ANP Agent
  DID: did:wba:localhost:agent:e1_XyZ789AbC
  端点: http://localhost:8900
  安全方案: didwba_sc
  RPC 入口: http://localhost:8900/agent/rpc
  支持方法: chat, anp.get_capabilities
```

> **设计原理**：`discover` 内部执行两个 HTTP 请求：
> 1. `GET /agent/ad.json` 获取 Agent Description，从中提取 `did`、`endpoint`、`security` 和 `interfaces`
> 2. `GET /agent/interface.json` 获取 OpenRPC 方法列表
>
> 验证逻辑包括：`protocolType == "ANP"`、DID 格式为 `did:wba:`、端点在允许范围内（loopback HTTP 或任意 HTTPS）。如果服务端未实现某个方法，OpenRPC 中不会声明，调用方据此判断可用能力。

---

### Step 5：发送 Chat 请求

用调用方 DID 身份签名一个 JSON-RPC chat 请求，发送到服务智能体。

**命令**：

```bash
python3 clients/anp-client/scripts/anp_client.py chat \
  --endpoint http://127.0.0.1:8900 \
  --message "你好，请介绍一下你自己"
```

**预期输出**：

```
[认证] 使用身份: did:wba:localhost:agent:e1_B8xK2mP9vR4q
[签名] 已生成 DID WBA HTTP Message Signature
[请求] POST http://127.0.0.1:8900/agent/rpc
[响应] 200 OK

回复:
你好！我是运行在 Hermes 上的 ANP 服务智能体。我通过 ANP 协议对外提供
标准的服务发现和 JSON-RPC 调用接口...
```

> **设计原理**：完整链路回溯（详见[端到端调用时序图](diagrams/02-e2e-call-sequence.md)）：
>
> 1. **加载身份** — 从 `~/.anp-client/` 读取 DID 文档和 Ed25519 私钥
> 2. **构造 JSON-RPC body** — `{"jsonrpc":"2.0","method":"chat","params":{"message":"你好..."},"id":"chat-<uuid>"}`
> 3. **DID WBA 签名** — 使用 `DIDWbaAuthHeader` 对请求方法、路径、Content-Type、Content-Digest 签名
> 4. **POST 请求** — 携带 `Signature` 和 `Signature-Input` 头发送到 `/agent/rpc`
> 5. **服务端认证** — `ANPAuth.authenticate()` 解析调用方 DID → 获取 DID 文档 → 验证签名和 proof
> 6. **桥接 Hermes** — `ANPBridge.call()` 创建 `asyncio.Future`，构造 `MessageEvent` 注入 Hermes 消息流
> 7. **LLM 处理** — Hermes 核心运行 LLM 推理并生成回复
> 8. **结果返回** — `ANPAdapter.send()` 通过 `bridge.set_result()` 完成 Future，构造 JSON-RPC 响应
>
> 关键设计点：
> - 客户端 JSON-RPC `id`（如 `chat-<uuid>`）与服务端内部 `request_id`（如 `req-1`）隔离，避免并发冲突
> - `chat_id` 格式为 `anp:req-N`，`adapter.send()` 解析此前缀将回复路由回正确的 Future
> - `asyncio.shield()` 保护 Future 防止外部 CancelledError 污染内部 pending 状态

---

### Step 6：查询服务能力

通过 `anp.get_capabilities` 查询服务智能体的能力声明。

**命令**（需要一个辅助脚本签名并发送）：

```bash
python3 -c "
import asyncio, json, os, sys
sys.path.insert(0, 'clients/anp-client/scripts')

from did_identity import load_or_create_identity
from signing import build_signed_headers
import aiohttp

async def main():
    identity = load_or_create_identity()
    body = json.dumps({
        'jsonrpc': '2.0',
        'method': 'anp.get_capabilities',
        'params': {
            'meta': {
                'profile': 'anp.core.binding.v1',
                'security_profile': 'transport-protected'
            },
            'body': {}
        },
        'id': 'caps-1'
    })
    url = 'http://127.0.0.1:8900/agent/rpc'
    headers = await build_signed_headers(identity, url, body)
    headers['Content-Type'] = 'application/json'
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=body, headers=headers) as r:
            print(json.dumps(await r.json(), indent=2, ensure_ascii=False))

asyncio.run(main())
"
```

**预期输出**：

```json
{
  "jsonrpc": "2.0",
  "id": "caps-1",
  "result": {
    "service_did": "did:wba:localhost:agent:e1_XyZ789AbC",
    "supported_profiles": ["anp.core.binding.v1"],
    "supported_security_profiles": ["transport-protected"],
    "limits": {
      "max_request_bytes": "1048576"
    },
    "supported_content_types": ["text/plain", "application/json"]
  }
}
```

> **设计原理**：
> - `anp.get_capabilities` 是 ANP Core Binding v1 规定的标准能力查询方法，所有 ANP 服务智能体都应支持
> - `supported_profiles` — 当前只支持 `anp.core.binding.v1`（明文 JSON-RPC，不包含 E2EE）
> - `supported_security_profiles` — `transport-protected` 表示依赖传输层（TLS）保护消息，不实现消息级端到端加密
> - `limits.max_request_bytes` — 1MB 请求体上限
> - 如果 tool RPC 开启并配置了 allowlist，结果会额外包含 `hermes_tools` 字段

---

## 错误演示：理解安全边界（3 步）

---

### 错误演示 1：缺少签名 → `-32003`

演示未携带 DID WBA 签名时服务端如何拒绝。

**命令**：

```bash
curl -s -X POST http://127.0.0.1:8900/agent/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"chat","params":{"message":"hi"},"id":"err-1"}' \
  | python3 -m json.tool
```

**预期输出**：

```json
{
  "jsonrpc": "2.0",
  "id": "err-1",
  "error": {
    "code": -32003,
    "message": "缺少认证头"
  }
}
```

同时服务端返回 HTTP 401。

> **设计原理**：
> - `-32003` 由 `auth.py:_classify_verifier_error()` 根据 `DidWbaVerifierError` 的异常消息分类生成
> - 请求缺少 `Signature` 或 `Signature-Input` 头时触发
> - HTTP 401 响应中可能附带 `WWW-Authenticate` 和 `Accept-Signature` challenge 头（当签名头存在但格式错误时），但完全缺失时不附带

---

### 错误演示 2：无效签名 → `-32001`

演示签名内容被篡改时服务端如何检测并拒绝。

**命令**：

```bash
# 用错误密钥签名（手工篡改签名头）
# 这里用一个明显无效的 Signature 头来演示
curl -s -X POST http://127.0.0.1:8900/agent/rpc \
  -H "Content-Type: application/json" \
  -H 'Signature: sig1=:AAAA:' \
  -H 'Signature-Input: sig1=("content-type");created=9999999999' \
  -d '{"jsonrpc":"2.0","method":"chat","params":{"message":"hi"},"id":"err-2"}' \
  | python3 -m json.tool
```

**预期输出**：

```json
{
  "jsonrpc": "2.0",
  "id": "err-2",
  "error": {
    "code": -32001,
    "message": "DID WBA 签名无效"
  }
}
```

> **设计原理**：服务端通过 `DidWbaVerifier.verify_request()` 验证签名。验证过程包括：
> 1. 从 `Signature-Input` 和 `Signature` 头提取签名参数和签名值
> 2. 按签名头声明的内容重建签名基串
> 3. 从解析到的 DID 文档获取 `verificationMethod` 中的公钥
> 4. 用公钥验证签名——签名内容、算法或公钥任何一项不匹配都会导致验证失败

---

### 错误演示 3：不支持的 Core Binding profile → `1001`

演示使用未实现的 ANP profile 时服务端的响应。

**命令**：

```bash
# 需要签名，用 anp-client 辅助
python3 -c "
import asyncio, json, sys
sys.path.insert(0, 'clients/anp-client/scripts')

from did_identity import load_or_create_identity
from signing import build_signed_headers
import aiohttp

async def main():
    identity = load_or_create_identity()
    body = json.dumps({
        'jsonrpc': '2.0',
        'method': 'chat',
        'params': {
            'meta': {
                'profile': 'anp.unknown.future.v99',
                'security_profile': 'transport-protected'
            },
            'body': {'message': 'test'}
        },
        'id': 'err-3'
    })
    url = 'http://127.0.0.1:8900/agent/rpc'
    headers = await build_signed_headers(identity, url, body)
    headers['Content-Type'] = 'application/json'
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=body, headers=headers) as r:
            print(json.dumps(await r.json(), indent=2, ensure_ascii=False))

asyncio.run(main())
"
```

**预期输出**：

```json
{
  "jsonrpc": "2.0",
  "id": "err-3",
  "error": {
    "code": 1001,
    "message": "不支持的 ANP profile",
    "data": {
      "anp_code": "anp.unsupported_profile",
      "retryable": false
    }
  }
}
```

> **设计原理**：
> - `1001` 是 ANP Core Binding 公共错误码（非 JSON-RPC 2.0 标准码），携带 `error.data.anp_code` 辅助客户端分类
> - `retryable: false` 表示这不是临时性错误，重试不会成功
> - 启用 Core Binding envelope（`params.meta/body`）时才会触发 profile 校验；如果使用旧版扁平 `params.message` 格式则跳过校验，保持向后兼容
> - 同理，`1002`（不支持的安全 profile）和 `1003`（params 形态无效）也遵循相同模式

---

## Tool RPC 演示：安全分层验证（2 步）

---

### Tool RPC 演示 1：默认关闭状态

验证 tool RPC 默认关闭，任何 `hermes.tool.*` 方法都返回"方法不存在"。

**验证默认状态**：

```bash
# 查看 interface.json，确认只有 chat 和 anp.get_capabilities
curl -s http://127.0.0.1:8900/agent/interface.json \
  | python3 -c "import sys,json; [print(f'  - {m[\"name\"]}') for m in json.load(sys.stdin)['methods']]"
```

**预期输出**：

```
  - chat
  - anp.get_capabilities
```

**尝试调用 tool 方法**：

```bash
curl -s -X POST http://127.0.0.1:8900/agent/rpc \
  -H "Content-Type: application/json" \
  -H 'Signature: sig1=:AAAA:' \
  -H 'Signature-Input: sig1=("content-type");created=9999999999' \
  -d '{"jsonrpc":"2.0","method":"hermes.tool.skills_list","params":{},"id":"err-tool-1"}' \
  | python3 -m json.tool
```

**预期输出**：

```json
{
  "jsonrpc": "2.0",
  "id": "err-tool-1",
  "error": {
    "code": -32601,
    "message": "方法不存在: hermes.tool.skills_list"
  }
}
```

> **设计原理**：
> - `-32601` 是 JSON-RPC 2.0 标准的"方法不存在"错误码，与签名无效的 `-32001` 区分
> - 无论 tool_rpc 是否启用、工具是否存在、caller DID 是否授权，未允许的工具统一返回 `-32601`——不泄露内部信息
> - 设计理念是"默认拒绝"（deny-by-default）：需显式配置才能暴露能力，而非配置哪些不能暴露

---

### Tool RPC 演示 2：开启并调用

配置 tool_rpc，暴露低风险工具，验证完整调用链路。

**修改 `~/.hermes/config.yaml`**：

```yaml
gateway:
  platforms:
    anp:
      enabled: true
      extra:
        hostname: localhost
        port: 8900
        tool_rpc:
          enabled: true
          allowed_dids:
            - did:wba:localhost:agent:e1_B8xK2mP9vR4q   # 替换为你的调用方 DID
          allowed_tools:
            - skills_list                                # 低风险的只读工具
```

**重启 Hermes gateway 并验证**：

```bash
# 重启后检查 interface.json
curl -s http://127.0.0.1:8900/agent/interface.json \
  | python3 -c "import sys,json; [print(f'  - {m[\"name\"]}') for m in json.load(sys.stdin)['methods']]"
```

**预期输出**（新增 `hermes.tool.skills_list`）：

```
  - chat
  - anp.get_capabilities
  - hermes.tool.skills_list
```

**签名调用 tool**：

```bash
python3 -c "
import asyncio, json, sys
sys.path.insert(0, 'clients/anp-client/scripts')

from did_identity import load_or_create_identity
from signing import build_signed_headers
import aiohttp

async def main():
    identity = load_or_create_identity()
    body = json.dumps({
        'jsonrpc': '2.0',
        'method': 'hermes.tool.skills_list',
        'params': {},
        'id': 'tool-call-1'
    })
    url = 'http://127.0.0.1:8900/agent/rpc'
    headers = await build_signed_headers(identity, url, body)
    headers['Content-Type'] = 'application/json'
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=body, headers=headers) as r:
            print(json.dumps(await r.json(), indent=2, ensure_ascii=False))

asyncio.run(main())
"
```

**预期输出**（格式为 `result.content`）：

```json
{
  "jsonrpc": "2.0",
  "id": "tool-call-1",
  "result": {
    "content": "...技能列表...",
    "tool": "skills_list",
    "metadata": {
      "request_id": "req-1"
    }
  }
}
```

> **设计原理**：五层安全策略（详见 [Tool RPC 安全架构图](diagrams/04-tool-rpc-architecture.md)）：
>
> 1. **配置开关** — `tool_rpc.enabled = true` 是第一道闸门
> 2. **调用方授权** — `allowed_dids` 限制哪些 DID 可以调用工具
> 3. **工具 Allowlist** — `allowed_tools` / `allowed_toolsets` 显式指定可暴露的工具
> 4. **工具 Denylist** — `denied_tools` + 内置 `HIGH_RISK_TOOL_DENYLIST`（`terminal`、`execute_code`、`write_file` 等），优先级高于 Allowlist
> 5. **执行时校验** — 参数 Schema 校验、超时、结果大小限制、异常安全包装
>
> Tool RPC 调用成功时附带 `Authentication-Info` 响应头；调用失败时不附带（避免泄露认证状态）。

---

## 清理

```bash
# 停止 DID 文档服务
kill %1 2>/dev/null || pkill -f "anp_client.py serve-did"

# 停止 Hermes gateway
pkill -f "hermes gateway run"

# 可选：清除测试身份文件
rm -rf ~/.anp-client/
rm -rf ~/.hermes/data/anp-agent/
```

---

## 附录

### 架构图索引

- [组件架构图](diagrams/01-component-architecture.md) — 三层组件关系与数据流
- [端到端调用时序图](diagrams/02-e2e-call-sequence.md) — 7 阶段完整调用序列
- [错误路径全景](diagrams/03-error-paths.md) — 14 种错误码与触发条件
- [Tool RPC 安全架构](diagrams/04-tool-rpc-architecture.md) — 五层纵深防御

### 完整配置参考

所有可通过环境变量覆盖的配置项：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `ANP_HOST` | `0.0.0.0` | HTTP 绑定地址 |
| `ANP_PORT` | `8900` | HTTP 绑定端口（0 = 动态分配） |
| `ANP_HOSTNAME` | `localhost` | 用于生成 DID 的主机名 |
| `ANP_ENDPOINT` | `http://{hostname}:{port}` | 对外公开的访问地址 |
| `ANP_DATA_DIR` | `~/.hermes/data/anp-agent/` | DID 身份存储目录 |
| `ANP_REQUEST_TIMEOUT` | `60` | Hermes 回复等待超时（秒） |
| `ANP_FUTURE_TTL` | `120` | 未完成请求的过期时间（秒） |
| `ANP_DID_RESOLVER_BASE_URL` | — | 本地测试 DID 解析覆盖（仅 loopback） |
| `ANP_ALLOW_ALL_USERS` | — | 跳过调用方 DID 白名单校验 |
| `ANP_ALLOWED_USERS` | — | 允许的调用方 DID 列表（逗号分隔） |
| `ANP_DID_RESOLVE_TIMEOUT` | `10` | DID 文档解析超时（秒，最大 60） |
| `ANP_TOOL_RPC_ENABLED` | — | 工具 RPC 开关 |
| `ANP_TOOL_RPC_TIMEOUT` | `30` | 单次工具调用超时（秒） |
| `ANP_TOOL_RPC_MAX_RESULT_BYTES` | `65536` | 工具结果大小上限（字节） |

### 常见问题排查

**Q: `hermes gateway run` 找不到命令**

确认 Hermes 已正确安装（`pip install hermes-agent` 或从源码安装），`which hermes` 应返回有效路径。

**Q: `/agent/ad.json` 返回 404**

检查 `~/.hermes/config.yaml` 中 `gateway.platforms.anp.enabled` 是否为 `true`，以及 anp-agent 插件是否已安装到 `~/.hermes/plugins/`。

**Q: Chat 请求返回 `-32002` DID 无法解析**

确认 `ANP_DID_RESOLVER_BASE_URL` 已正确设置，且 `anp-client serve-did` 仍在运行。可以用 `curl http://127.0.0.1:18900/agent/e1_<fingerprint>/did.json` 验证。

**Q: Chat 请求返回 `-32003` 缺少认证头**

确认 `anp-client chat` 命令中使用了 `--endpoint` 指向正确的地址（包含 `http://` 前缀），且调用方身份已通过 `whoami` 创建。
