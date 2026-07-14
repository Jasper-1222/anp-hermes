# ANP Client Skill

`anp-client` 是安装在个人智能体中的通用客户端 skill，用于通过 ANP DID WBA 签名调用安装 Hermes `anp-agent` plugin 的服务智能体。

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

## 安装包态本地验证最短路径

1. 在 Hermes 中安装 `anp-agent` plugin zip。
2. 本地测试时，Hermes gateway 启动前设置：

```bash
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

3. 在 OpenClaw 中安装 `anp-client` skill zip。
4. 在 OpenClaw 对话中启动本地 DID 文档服务，默认监听 `127.0.0.1:18900`。
5. 对 OpenClaw 说：

```text
通过 ANP 调用 http://localhost:8900 的服务智能体，问它“请介绍下自己”
```

如果 Hermes 已经在运行后才设置环境变量，需要重启 Hermes gateway。`localhost` 与 `127.0.0.1` 在本地同端口场景会被视为等价。

## 最小本地流程

```bash
python3 scripts/anp_client.py whoami
python3 scripts/anp_client.py serve-did
```

在本地服务智能体启动环境中设置：

```bash
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
export ANP_ALLOW_ALL_USERS=1
```

发现服务智能体：

```bash
python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
```

发送 chat：

```bash
python3 scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好"
```

## 边界

第一期只支持直接 URL、发现和 `chat`。不支持 `hermes.tool.*`、通讯录、AP2、E2EE、群聊或多轮 session 同步。

默认个人智能体 DID 为本地开发用 `did:wba:localhost...`。Phase 1 signed `chat` 验收只承诺同机 loopback 服务智能体；HTTPS endpoint 虽然通过传输安全校验，但远程服务通常无法解析该 localhost DID。生产/跨机器调用需要后续提供公开 DID 文档托管或显式 hostname 初始化能力。

## 故障排查

### DID 文档无法解析（`-32002`）

先运行：

```bash
python3 scripts/anp_client.py serve-did
```

然后确保本地服务智能体启动环境中设置：

```bash
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

### 签名无效（`-32001`）

检查 `~/.anp-client/did.json` 与 `~/.anp-client/private_key.pem` 是否匹配，确认请求 body 在签名后没有被修改。

### 缺少认证头（`-32003`）

必须通过 `python3 scripts/anp_client.py chat ...` 发送 DID WBA 签名请求，不要直接用裸 HTTP POST 调用 `/agent/rpc`。

### endpoint 被拒绝

第一期只允许 loopback HTTP 和 HTTPS：

- `http://127.0.0.1:<port>`
- `http://localhost:<port>`
- `http://[::1]:<port>`
- `https://<host>`

`http://example.com`、局域网 IP 和公网明文 HTTP 会被拒绝。

### `serve-did` 的生产边界

`serve-did` 仅用于本地开发、测试和 E2E。默认生成的个人智能体 DID 为 `did:wba:localhost...`，同机服务智能体可通过 `ANP_DID_RESOLVER_BASE_URL` 解析。HTTPS endpoint 虽然通过传输安全策略校验，但远程服务通常无法解析本机 localhost DID；生产/跨机器调用需要后续提供公开 DID 文档托管或显式 hostname 初始化能力。
