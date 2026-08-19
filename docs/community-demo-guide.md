# ANP Hermes 社区演示主持指南

本文档是面向社区演示的主持稿：先讲清楚项目在验证什么、解决什么问题，再通过 Live Demo 让观众亲眼看到完整链路。全流程控制在 **15 分钟**以内。

与 [demo-walkthrough.md](demo-walkthrough.md) 的区别：演练脚本是"命令 + 预期输出 + 设计原理"的技术教程；本指南是"分幕、话术、时间控制、风险预案"的主持脚本。

## 总结构：三段式（先讲清"为什么"，再让观众"亲眼看到"）

```text
0:00 ─ 4:00   第一段：总体架构图 —— 项目在验证什么、解决什么问题
4:00 ─ 12:00  第二段：Live Demo 四步 —— 把刚才讲的旅程现场走一遍
12:00 ─ 15:00 第三段：收尾 —— 一句话结论 + 自己怎么动手
```

## 第一段（4 分钟）：一张架构图讲透"验证什么、解决什么问题"

### 开场一句话定位（30 秒）

> 这个项目回答一个问题：**真实的智能体运行时（Hermes）能不能通过标准插件机制接入 ANP 网络，被其他智能体发现、认证、调用？**

### "在验证什么"——ANP 协议链路五个环节

每环节给一句话 + 一个观众熟悉的概念：

| 环节 | 要验证的内容 | 一句话类比 |
| --- | --- | --- |
| 身份 | Hermes 如何获得 ANP 原生身份（DID WBA） | 智能体的身份证 |
| 发现 | 调用方怎么找到服务、知道它支持什么 | 名片 + API 说明书 |
| 认证 | 怎么证明请求确实是声称的调用方发的 | 私钥盖章，公钥验章 |
| 调用 | ANP 请求如何进入 Hermes 消息流 | 翻译官 |
| 回复 | Hermes 的回复如何原路返回 | 回执 |

### 总体架构图讲述要点（2.5 分钟）

使用 [组件架构图](diagrams/01-component-architecture.md)（建议提前渲染为 PNG 放入幻灯片），按两条线讲：

- **调用线**：蓝色调用方（anp-client：身份 + 签名 + 本地 DID 文档服务）→ 橙色服务端插件（anp-agent：5 条路由 + 认证 + 桥接）→ 绿色 Hermes Core（消息管道 + LLM）
- **认证支线**：服务端认证时向调用方 DID 文档服务取公钥验章——本地由 `serve-did` 提供，生产按 DID WBA HTTPS 规则从公开地址解析
- **返回线**：回复 → bridge 回写 → JSON-RPC 响应
- **落点（社区价值）**："整个插件**零侵入** Hermes 核心代码，走公开插件接口——这就是给其他智能体框架的接入样板。"

## 第二段（8 分钟）：四步 Live Demo

> 开场一句："下面把刚才这张图，用真实命令走一遍。"

| 时间 | 命令 | 演示后的一句话讲解 |
| --- | --- | --- |
| 4:00 | `python3 clients/anp-client/scripts/anp_client.py whoami` | 第一次运行自动生成身份——身份证号和公钥就绪，私钥留在本机（0o600 权限），谁也没见过 |
| 4:40 | `python3 clients/anp-client/scripts/anp_client.py discover --endpoint http://127.0.0.1:8900` | 拿到了名片（我是谁、在哪、用什么安全方案）和说明书（支持 chat、get_capabilities）。可先 `curl http://127.0.0.1:8900/agent/interface.json` 让观众直接看到端点 |
| 5:30 | `python3 clients/anp-client/scripts/anp_client.py chat --endpoint http://127.0.0.1:8900 --message "你好，请介绍一下自己"` | 核心环节，利用 LLM 响应的等待时间讲 [端到端时序图](diagrams/02-e2e-call-sequence.md) 的四站路（见下） |
| 9:30 | `curl -s -X POST http://127.0.0.1:8900/agent/rpc -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"chat","params":{"message":"hi"},"id":"err-1"}'` | 没带身份证明 → `-32003`。**金句**："这个插件默认什么都不信——认证、能力、工具，每一样都要显式打开" |

### chat 环节的节奏设计（重点）

发完消息后 LLM 有 5-30 秒响应延迟——**这段时间正好讲时序图**的四站路：

1. 私钥盖章（HTTP Message Signatures）
2. 服务器解析 DID → 拿公钥验章
3. 请求翻译成 Hermes 消息（bridge 桥接）
4. LLM 生成回复，原路返回

回复到达时正好衔接结果展示。**左侧终端永远开着 Hermes gateway 日志**，观众能看到"认证通过 → 消息进入 → 回复生成"的实时痕迹。

## 真实 LLM 专项预案（五个风险 × 对策）

| 风险 | 对策 |
| --- | --- |
| **延迟**（5-30 秒不可控） | 演示前一天连发 5 次实测，记录 P95；等待时讲时序图救场；超 60 秒无响应 → 切录屏 |
| **额度 / 认证** | 提前验证 API key 有效、额度充足、provider 无维护公告（参考 CLAUDE.md 中 `ANP_E2E_LLM_PROVIDER` 等环境变量覆盖示例） |
| **回复内容不可控** | 固定 2 个确定性演示问题（如"你好，请介绍一下自己"），现场不即兴发挥 |
| **会话残留** | 正式演示前**重启 Hermes gateway 清上下文**——避免彩排内容污染正式回复（最容易被忽略） |
| **网络中断** | LLM 失败会返回结构化 JSON-RPC 错误——本身可讲"失败不伪装成成功"；另备 mock LLM 配置，1 分钟可切回 |

## 第三段（3 分钟）：收尾

1. **一句话结论**："ANP 协议链路在真实 Hermes 运行时上全通——发现、认证、调用、回复，且零侵入。本仓库就是给其他智能体框架的接入参考实现。"
2. **10 秒动手指引**：Hermes 对话框发一句 `安装插件 <zip 链接>` 即装；完整教程在 README 快速体验与 [demo-walkthrough.md](demo-walkthrough.md)
3. **贡献入口**：OpenSpec 流程、中文提交约定、欢迎 PR；留 2 分钟答疑

## 准备清单（按顺序执行）

- [ ] **演示前一天**：按 demo-walkthrough 用现场真实命令彩排一遍完整链路
- [ ] **演示前一天**：`python3 -m pytest plugins/anp-agent/tests/e2e/test_echo.py -v --run-e2e` 确定性自检（mock LLM，无需 API key）
- [ ] **演示前一天**：连发 5 次 chat 实测 LLM 延迟；验证 API key 与额度
- [ ] **演示前一天**：彩排全程录屏（环境故障保底）；两张 Mermaid 架构图渲染 PNG；`anp.get_capabilities` 长命令预先落盘为脚本；备 3 张预期输出截图
- [ ] **演示当天**：重启 Hermes gateway 清会话 → 双终端布局（左 gateway 日志 / 右 anp-client 命令）→ 终端字号调大、关闭通知 → 确认录屏文件路径

**一句话现场口诀**：架构图先立心智 → 四步命令走旅程 → LLM 等待讲原理 → 无签名演示立安全 → 安装指引收尾。

## 附录：通俗化话术速查表

术语首次出现时用一句话带过，避免术语堆砌：

| 术语 | 一句话说法 |
| --- | --- |
| DID WBA | 智能体的身份证号，用域名做身份锚点 |
| 签名（HTTP Message Signatures） | 用私钥给请求"盖章" |
| Agent Description（ad.json） | 智能体的名片 |
| OpenRPC（interface.json） | 智能体的 API 说明书 |
| well-known 发现 | 智能体黄页 |
| JSON-RPC | 智能体之间打电话的固定格式 |
| tool RPC | 把 Hermes 的技能（工具）变成可远程调用的 API |

## 附录：本机演示环境启动（2026-08-12 实测可用）

本机环境（macOS / Hermes v0.20.0 源码安装于 `~/.hermes/hermes-agent/`）已搭建并验证。**每次演示前按顺序执行**：

```bash
# 1. 启动调用方 DID 文档服务（服务端认证需要解析调用方 DID）
~/.hermes/hermes-agent/venv/bin/python3 clients/anp-client/scripts/anp_client.py serve-did --port 18900 &

# 2. 启动 Hermes gateway（关键：NO_PROXY 绕过 macOS 系统代理，否则 LLM 请求 502）
NO_PROXY="127.0.0.1,localhost" \
ANP_ALLOW_ALL_USERS=1 \
ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900 \
~/.hermes/hermes-agent/venv/bin/hermes gateway run
```

**已验证的环境要点**：
- `hermes` 不在 PATH，用 `~/.hermes/hermes-agent/venv/bin/hermes`（或加入 PATH）
- **LLM 凭据**：复用 Claude Code 会话凭据（`~/.hermes/.env` 中 `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL`），经本机 cc-switch 代理（127.0.0.1:15721）转发到上游；**cc-switch 需保持运行**，Claude Code 会话 token 过期时需刷新 `.env`
- **NO_PROXY 必须设置**：macOS 系统代理（127.0.0.1:7897）会导致 anthropic SDK（httpx）LLM 请求 502；已写入 `~/.hermes/.env`
- 插件安装：`ln -s <仓库>/plugins/anp-agent ~/.hermes/plugins/anp-agent`，并在 `~/.hermes/config.yaml` 配置 `plugins.enabled: [anp-agent]` + `gateway.platforms.anp`（用户级平台插件必须显式启用）
- 实测延迟：真实 LLM 单轮 2.2~2.8 秒（2026-08-12，DeepSeek 上游）
- 首次会话会提示设置 home channel，发送 `/sethome` 一次即可

## 参考

- [组件架构图](diagrams/01-component-architecture.md)
- [端到端调用时序图](diagrams/02-e2e-call-sequence.md)
- [错误路径全景](diagrams/03-error-paths.md)
- [Tool RPC 安全架构](diagrams/04-tool-rpc-architecture.md)
- [Demo 演练脚本](demo-walkthrough.md)
