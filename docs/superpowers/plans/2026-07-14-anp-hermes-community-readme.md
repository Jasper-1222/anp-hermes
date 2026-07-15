# ANP Hermes 社区 README 更新实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将根 README 更新为面向所有 ANP 社区成员的 ANP × Hermes 技术验证 demo 介绍与体验入口。

**Architecture:** 仅重组和改写根 `README.md`，先用正向叙事解释项目目的、解决的问题和协议交互链路，再保留当前实现能力、快速体验、打包、测试、配置和社区参与信息。所有技术事实和命令以当前仓库实现为准，不修改任何运行时代码或测试。

**Tech Stack:** Markdown、Hermes 插件机制、ANP Python SDK、DID WBA、OpenRPC、JSON-RPC 2.0。

## Global Constraints

- 面向 ANP 社区所有成员，而不是针对某位负责人撰写采纳申请。
- 使用“ANP × Hermes 技术验证 demo”作为核心定位。
- 正向说明项目目的、目标、解决的问题、实现方式和体验方法。
- 不专门强调“不是生产级网关”，不组织长篇未实现能力清单。
- tool RPC 只作为默认关闭的可选体验能力，不作为首屏主叙事。
- 保留必要的本地测试、安全配置、私钥保护和 DID resolver 使用说明。
- 不夸大能力，不把条件执行的真实 LLM E2E 描述为无条件通过。
- 只修改根 `README.md`；不修改业务代码、测试、插件 README、OpenSpec capability specs 或打包脚本。
- 官方语言为中文。

---

## File Structure

- Modify: `README.md` — 面向 ANP 社区的项目总览、交互方式、体验步骤与验证说明。
- Reference only: `plugins/anp-agent/README.md` — 核对详细插件配置与命令，不修改。
- Reference only: `docs/anp-hermes-current-implementation-analysis.md` — 核对能力和验证边界，不修改。

### Task 1: 重写根 README 的社区介绍与体验叙事

**Files:**
- Modify: `README.md:1-166`
- Reference: `plugins/anp-agent/README.md`
- Reference: `docs/anp-hermes-current-implementation-analysis.md`

**Interfaces:**
- Consumes: 当前插件已实现的 DID WBA 身份、发现端点、OpenRPC、JSON-RPC、`chat`、`anp.get_capabilities`、可选 tool RPC、打包和测试命令。
- Produces: 一个可直接公开给所有 ANP 社区成员阅读和运行的根 README。

- [ ] **Step 1: 改写标题、项目定位、项目目的和问题说明**

将 README 开头组织为以下信息层次，实际文案保持中文自然表达并与现有事实一致：

```markdown
# anp-hermes

ANP × Hermes 技术验证 demo：通过 Hermes 插件机制，让 Hermes 智能体作为 ANP 服务智能体被发现、认证并通过 JSON-RPC 调用。

本项目面向 ANP 社区成员，用于体验 ANP 协议与真实智能体运行时 Hermes 的交互方式，展示 DID WBA 身份、Agent 发现、OpenRPC 描述和 JSON-RPC 调用在 Hermes 插件中的落地方式。

## 项目目的

- 提供一个可以本地运行和验证的 ANP × Hermes 交互 demo。
- 展示真实智能体运行时如何通过插件机制接入 ANP。
- 帮助社区理解 DID WBA、Agent Description、OpenRPC 与 JSON-RPC 如何组合成完整调用链路。
- 为其他智能体框架接入 ANP 提供可参考的实现思路。

## 解决什么问题

说明协议文档和 SDK 示例之外，社区还需要一个真实 Agent runtime 接入样例；说明本项目连接 ANP 调用方与 Hermes 消息处理流程，让发现、认证、调用和响应可以被完整体验。
```

- [ ] **Step 2: 增加交互链路图并重组实现方式**

加入以下语义完整的 ASCII 链路图：

```text
ANP Client / RemoteAgent
        │
        │ 1. 发现 Agent Description 与 OpenRPC 接口
        ▼
Hermes ANP Plugin
        │
        │ 2. 验证 DID WBA 调用方身份
        │ 3. 接收 chat / anp.get_capabilities JSON-RPC 请求
        ▼
Hermes Agent Runtime
        │
        │ 4. 处理消息并生成回复
        ▼
ANP JSON-RPC Response
```

随后用“实现方式”或同等正向标题说明：

- 插件通过 Hermes 公开插件接口注册 `anp` 平台；
- 自动生成和持久化 `did:wba:` 身份；
- 暴露 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json` 和 `/agent/rpc`；
- 在 RPC 入口执行 DID WBA HTTP Message Signatures 认证；
- 通过 bridge 把 JSON-RPC 请求送入 Hermes 消息处理流程；
- 支持 `chat`、`anp.get_capabilities` 和可选 `hermes.tool.*`。

- [ ] **Step 3: 保留并整理可运行体验内容**

将现有命令按以下顺序保留和整理，不改变有效参数：

1. `git clone` 与开发依赖安装；
2. 基础测试和覆盖率命令；
3. release zip 打包命令与产物；
4. Hermes 插件链接和 gateway 配置；
5. `ANP_ALLOW_ALL_USERS=1 hermes run` 本地体验命令；
6. Echo E2E；
7. 条件执行的真实 LLM E2E。

将相关标题调整为面向 demo 体验的“快速体验”“本地启动 Hermes + ANP 插件”“测试与验证”等正向标题。

- [ ] **Step 4: 整理配置、安全说明与社区参与内容**

保留以下必要事实，但不要将其组织为首屏免责声明：

- DID 文档和私钥默认写入 `~/.hermes/data/anp-agent/`；
- `ANP_DID_RESOLVER_BASE_URL` 只用于 loopback 本地开发、测试床和 E2E；
- tool RPC 默认关闭，启用时需要 caller DID 和工具 allowlist；
- release zip 会拒绝 DID 文档、私钥、缓存、本机绝对路径和真实私钥块。

将原“贡献”段落改成面向社区所有成员的参与说明，表达：

```markdown
## 社区参与

欢迎 ANP 社区成员运行和体验这个 demo，并围绕 DID WBA、Agent 发现、OpenRPC、JSON-RPC、ANP Core Binding 以及真实智能体运行时接入方式提出反馈和改进建议。
```

保留测试、lint 和中文提交约定。

- [ ] **Step 5: 检查 README 内容与格式**

运行：

```bash
python3 - <<'PY'
from pathlib import Path

text = Path("README.md").read_text(encoding="utf-8")
required = [
    "技术验证",
    "项目目的",
    "解决什么问题",
    "DID WBA",
    "Agent Description",
    "OpenRPC",
    "JSON-RPC",
    "快速体验",
    "社区参与",
]
missing = [item for item in required if item not in text]
assert not missing, f"README 缺少必要内容: {missing}"
assert "sk-..." not in text, "README 不应包含 API key 示例值"
print("README 内容检查通过")
PY
```

Expected: `README 内容检查通过`

运行：

```bash
git diff --check
```

Expected: 无输出，退出码为 0。

- [ ] **Step 6: 核对修改范围**

运行：

```bash
git status --short
git diff -- README.md
```

Expected:

- 业务实现文件、测试和插件 README 没有变化；
- README 首屏明确技术验证 demo 定位；
- README 包含项目目的、解决的问题、交互链路、实现方式和体验步骤；
- 所有保留命令与当前仓库实现一致。

- [ ] **Step 7: 运行文档相关验证**

运行：

```bash
openspec validate --all
```

Expected: 全部 OpenSpec specs/changes 校验通过。

本次只修改文档，不运行完整 Python 测试矩阵；若 README 中任何命令被修改，则逐项核对路径和参数与 `plugins/anp-agent/README.md`、`CLAUDE.md` 一致。

- [ ] **Step 8: 提交（仅在用户明确要求时）**

```bash
git add README.md docs/superpowers/specs/2026-07-14-anp-hermes-community-readme-design.md docs/superpowers/plans/2026-07-14-anp-hermes-community-readme.md
git commit -m "docs: 更新 ANP Hermes 技术验证项目说明"
```

Expected: 创建一个只包含 README、设计文档和实施计划的中文文档提交。未经用户明确要求，不执行本步骤。
