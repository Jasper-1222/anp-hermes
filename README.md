# anp-hermes

**ANP × Hermes 技术验证 Demo**：通过 Hermes 插件机制，让 Hermes 智能体成为可被发现、认证和调用的 ANP 服务智能体。

本项目面向 [ANP（Agent Network Protocol）](https://github.com/agent-network-protocol) 社区，用一个可运行、可测试的端到端示例，展示 ANP 协议与真实智能体运行时 [Hermes](https://github.com/NousResearch/hermes-agent) 的交互方式。仓库同时提供 Hermes 服务端插件和 ANP 调用端 skill，方便社区成员体验从 Agent 发现、DID WBA 身份认证到 JSON-RPC 对话的完整链路。

## 项目目的

让 ANP 社区成员能够通过一个真实智能体运行时，直观体验 ANP 协议从服务发现、身份认证到消息调用和回复的完整过程。

## 项目目标

- 提供一个可以在本地运行和验证的 ANP × Hermes 交互 demo。
- 展示真实智能体运行时如何通过插件机制接入 ANP 网络。
- 帮助社区理解 DID WBA、Agent Description、OpenRPC 和 JSON-RPC 如何组合成完整的智能体调用链路。
- 为其他智能体框架接入 ANP 提供可参考的实现思路。

## 解决什么问题

协议文档和 SDK 示例能够说明 ANP 的数据结构与接口，但要理解协议如何连接真实智能体，还需要回答几个具体问题：

- Hermes 智能体如何获得并管理 ANP 原生身份？
- 调用方如何发现一个 Hermes 服务智能体及其接口？
- DID WBA 签名请求如何在服务端完成身份验证？
- ANP JSON-RPC 请求如何进入 Hermes 消息处理流程？
- Hermes 生成的回复如何返回给 ANP 调用方？

`anp-hermes` 将这些环节连接为一套可直接体验的实现：

| 角色 | 项目组件 | 作用 |
| --- | --- | --- |
| 调用方智能体 | `clients/anp-client/` | 管理调用方 DID WBA 身份，发现服务智能体并发送签名请求 |
| 服务智能体 | `plugins/anp-agent/` | 将 Hermes 注册为 ANP 平台，提供发现、认证和 JSON-RPC 调用入口 |
| Hermes | Agent Runtime | 接收桥接后的消息，运行智能体并生成回复 |

## 交互方式

```text
用户 / 调用方智能体
        │
        │ 1. 通过 anp-client 发现服务智能体
        ▼
Agent Description / OpenRPC
        │
        │ 2. 使用调用方 DID WBA 身份签名请求
        ▼
Hermes ANP Plugin
        │
        │ 3. 验证身份并接收 chat JSON-RPC 请求
        │ 4. 将请求桥接为 Hermes MessageEvent
        ▼
Hermes Agent Runtime
        │
        │ 5. 处理消息并生成回复
        ▼
ANP JSON-RPC Response
```

调用方也可以通过 `anp.get_capabilities` 查询服务 DID、支持的 profile、安全 profile、内容类型和调用限制。

## 架构

详细架构图见 [docs/diagrams/](docs/diagrams/)：

- [组件架构](docs/diagrams/01-component-architecture.md) — 三层组件（Client / ANP Plugin / Hermes Core）及其数据流关系
- [端到端调用时序](docs/diagrams/02-e2e-call-sequence.md) — 从发现、认证到 JSON-RPC 响应的 7 阶段完整序列
- [错误路径全景](docs/diagrams/03-error-paths.md) — 各阶段 14 种错误码与速查表
- [Tool RPC 安全架构](docs/diagrams/04-tool-rpc-architecture.md) — 五层纵深防御策略

## 实现方式

### Hermes 服务端插件

`plugins/anp-agent/` 通过 Hermes 的公开插件接口注册 `anp` 平台，不修改 Hermes 核心代码：

- 自动生成并持久化管理 `did:wba:` DID WBA 身份，私钥保存在本地数据目录。
- 使用 DID WBA HTTP Message Signatures 验证调用方身份。
- 通过 `BasePlatformAdapter`、`MessageEvent` 和 `ctx.register_platform()` 将 ANP 请求接入 Hermes。
- 使用异步 bridge 关联 JSON-RPC 请求与 Hermes 回复。
- 支持 `chat` 和 `anp.get_capabilities` 方法。
- 可选将显式允许的低风险 Hermes tools 映射为 `hermes.tool.<tool_name>`。

插件提供以下 ANP 端点：

| 端点 | 用途 |
| --- | --- |
| `GET /agent/ad.json` | 返回 Agent Description，供已知地址的调用方直接发现 |
| `GET /.well-known/agent-descriptions` | 返回 JSON-LD CollectionPage，供调用方按域名发现 |
| `GET /agent/interface.json` | 返回 OpenRPC 接口文档 |
| `GET /agent/e1_<fingerprint>/did.json` | 按 DID WBA path DID 规则提供服务 DID 文档 |
| `POST /agent/rpc` | 接收经过 DID WBA 认证的 JSON-RPC 2.0 请求 |

### ANP 调用端 skill

`clients/anp-client/` 是面向个人智能体的通用调用端 skill，也可以直接通过命令行运行：

- 创建并持久化调用方 DID WBA 身份。
- 在本地提供调用方 DID 文档。
- 从 endpoint 或 Agent Description URL 发现服务智能体。
- 使用 DID WBA 身份签名并发送 `chat` 请求。
- 支持把常见自然语言表达归一化为发现或调用参数。

## 快速体验

### Hermes 安装插件

在 Hermes 对话框中发送：

```text
安装插件 https://github.com/Jasper-1222/anp-hermes/releases/latest/download/anp-agent.zip
```

或在本地手动安装：

```bash
git clone https://github.com/Jasper-1222/anp-hermes.git
ln -s "$(pwd)/anp-hermes/plugins/anp-agent" ~/.hermes/plugins/anp-agent
```

在 `~/.hermes/config.yaml` 中启用 `anp` 平台并重启 gateway 即可。

### OpenClaw / WorkBuddy 安装 skill

在对话框中发送：

```text
安装 skill https://github.com/Jasper-1222/anp-hermes/releases/latest/download/anp-client.zip
```

安装后即可通过自然语言发现和调用 ANP 服务智能体，例如：

```text
发现 http://localhost:8900 上的 ANP 服务智能体
通过 ANP 问它"你好，请介绍下自己"
```

更完整的分步演练请参考 [Demo 演练脚本](docs/demo-walkthrough.md)。

## 可选 Hermes tools RPC

插件支持将允许的 Hermes tool 暴露为 `hermes.tool.<tool_name>` JSON-RPC 方法（默认关闭）。详见 [插件 README](plugins/anp-agent/README.md)。

## 发布打包

从仓库根目录运行：

```bash
python3 scripts/package_anp_release.py
```

脚本会生成并校验：

- `dist/anp-agent-plugin-0.1.0.zip` — 版本化 Hermes 插件包
- `dist/anp-agent.zip` — 稳定插件别名
- `dist/anp-client-skill-0.1.0.zip` — 版本化客户端 skill 包
- `dist/anp-client.zip` — 稳定客户端别名

稳定别名与对应版本化资产内容相同。两个逻辑发布包都包含仓库根 MIT `LICENSE`。

## 仓库结构

```text
.
├── plugins/anp-agent/       # Hermes ANP 服务端平台插件
│   ├── anp_agent/           # 插件运行时 Python 包
│   ├── plugin.yaml          # Hermes 插件元数据
│   └── README.md            # 插件安装与配置说明
├── clients/anp-client/      # 个人智能体侧 ANP 调用 skill
│   ├── scripts/             # 身份、DID 文档服务、发现与调用脚本
│   └── SKILL.md             # skill 定义与自然语言调用样例
├── scripts/                 # 发布包构建与校验脚本
├── openspec/                # capability specs 与归档变更
└── .github/workflows/ci.yml # CI 配置
```

## 社区参与

欢迎 ANP 社区成员运行和体验这个 demo，并围绕 DID WBA、Agent 发现、OpenRPC、JSON-RPC、ANP Core Binding 以及真实智能体运行时接入方式提出反馈和改进建议。提交改进前请确保相关测试通过，且提交信息与文档使用中文。

## 许可证

[MIT](LICENSE)
