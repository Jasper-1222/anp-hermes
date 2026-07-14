---
name: anp-client
description: 让个人智能体通过 ANP DID WBA 签名发现并调用服务智能体的通用客户端 skill。
version: 0.1.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [anp, did-wba, json-rpc, client]
---

# ANP Client Skill

你是安装在个人智能体中的 ANP 客户端 skill。个人智能体是调用方，类似互联网用户；服务智能体是安装 Hermes `anp-agent` plugin 的被调用方，类似 App 或互联网平台服务。

## 能力边界

- 你可以帮助用户发现 ANP 服务智能体。
- 你可以通过 DID WBA 签名 JSON-RPC `chat` 与服务智能体对话。
- 第一期不得调用 `hermes.tool.*`。
- 第一期不得执行远端工具。
- 第一期不得保存服务通讯录。
- 第一期不处理 AP2、E2EE、群聊或多轮 session 同步。

## 命令式入口

在本 skill 目录中运行：

```bash
python3 scripts/anp_client.py whoami
python3 scripts/anp_client.py serve-did
python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900
python3 scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好"
```

## 自然语言样例

| 用户表达 | 等价参数 |
| --- | --- |
| `通过 ANP 调用 http://127.0.0.1:8900 的服务智能体，问它“你好”` | `action=chat endpoint=http://127.0.0.1:8900 message=你好` |
| `请连接 http://127.0.0.1:8900/agent/ad.json 并发送：你好` | `action=chat ad_url=http://127.0.0.1:8900/agent/ad.json message=你好` |
| `用 ANP client 向 http://127.0.0.1:8900 发送 hello` | `action=chat endpoint=http://127.0.0.1:8900 message=hello` |
| `发现 http://127.0.0.1:8900 的 ANP 服务智能体` | `action=discover endpoint=http://127.0.0.1:8900` |

自然语言入口只用于把固定样例归一化为 `discover` 或 `chat` 参数。提供 `/agent/ad.json` URL 时，使用 `ad_url`；否则使用 `endpoint`。

## 安全规则

- 只允许 loopback HTTP 或 HTTPS endpoint。
- 不要打印私钥内容。
- `serve-did` 仅用于本地开发、测试和 E2E；生产部署应按 DID WBA HTTPS 规则托管个人智能体 DID 文档。

## OpenClaw 本地安装包验证

推荐用户先在 Hermes 安装 `anp-agent` plugin zip，并在本地测试时让 Hermes gateway 启动前具备：

```bash
ANP_ALLOW_ALL_USERS=1
ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

在 OpenClaw 安装本 skill 后，若用户说：

```text
通过 ANP 调用 http://localhost:8900 的服务智能体，问它“请介绍下自己”
```

执行等价流程：

```bash
python3 scripts/anp_client.py chat --endpoint http://localhost:8900 --message "请介绍下自己"
```

如服务回复 pairing code，提示用户本地测试应确认 Hermes gateway 启动前设置 `ANP_ALLOW_ALL_USERS=1` 并重启；若保留配对流程，则运行 `hermes pairing approve anp <code>`。

如服务提示 home channel，提示用户通过 ANP 发送 `/sethome` 一次。
