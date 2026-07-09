# ANP Client Skill

`anp-client` 是安装在个人智能体中的通用客户端 skill，用于通过 ANP DID WBA 签名调用安装 Hermes `anp-agent` plugin 的服务智能体。

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

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
