# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目目标

本项目最终目标是**为 ANP（Agent Network Protocol）社区贡献一个高质量的 Hermes 接入参考实现**。具体而言，通过 Hermes 的平台插件机制，让 Hermes 智能体能够作为 ANP 网络上的**服务智能体**被其他智能体发现和调用。

关键约束：
- 使用 ANP 原生 DID WBA 身份（`did:wba:`），不使用 `did:cn` 或其他 DID 方法。
- 不依赖 DTR、Portal、Mediator、OpenClaw 等外部基础设施，仅使用 ANP Python SDK 和 Hermes 插件机制。
- 插件必须零侵入 Hermes 核心代码，便于社区贡献和独立发布。
- 第一期仅实现身份认证 + JSON-RPC 调用；AP2 支付和 E2EE 加密延后。

## 官方语言

本项目的官方语言为**中文**。所有文档、代码注释、业务语义命名、提交信息、Issue/PR 描述等均应使用中文。

## 开发命令

### 安装与测试

```bash
# 进入插件目录
cd plugins/anp-agent

# 安装插件及测试/开发依赖
python -m pip install -e ".[test,dev]"

# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_server.py -v

# 运行测试并检查覆盖率（覆盖率要求 ≥ 85%）
python -m pytest --cov=. --cov-fail-under=85 -q

# 阶段一：确定性 Echo E2E（本地 mock LLM，无需真实 API key）
python -m pytest tests/e2e/test_echo.py -v --run-e2e

# 阶段二：真实 LLM E2E（使用 ~/.hermes/config.yaml 中配置的 provider）
# 需要配置对应 provider 的 API key 环境变量，例如 DEEPSEEK_API_KEY
python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 阶段二：临时覆盖 provider（不修改 ~/.hermes/config.yaml）
export ANP_E2E_LLM_PROVIDER="kimi"
export ANP_E2E_LLM_API="https://api.kimi.com/coding/v1"
export ANP_E2E_LLM_KEY_ENV="KIMI_API_KEY"
export KIMI_API_KEY="sk-..."
python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```

### Lint 与格式化

```bash
# 检查 ruff lint
ruff check .

# 自动修复可修复的 lint 问题
ruff check --fix .

# 检查 black 格式化
black --check .

# 应用 black 格式化
black .
```

### 对话框安装（推荐）

在 Hermes 对话框中复制并发送以下内容，LLM 会自动完成下载、安装、启用与重启 Gateway：

```text
安装插件 https://github.com/OpenAnp/hermes-platform-anp-agent/releases/latest/download/anp-agent.zip
```

LLM 将按以下步骤执行：

1. 下载 `anp-agent.zip`。
2. 检查 zip 内包含 `plugin.yaml` 与 `__init__.py`。
3. 解压到 `~/.hermes/plugins/anp-agent/`。
4. 在 `~/.hermes/config.yaml` 中启用 `anp-agent` 插件，并添加 `gateway.platforms.anp` 配置。
5. 重启 Hermes gateway。
6. 报告成功或遇到的错误。

### 手动安装

```bash
# 将插件复制/链接到 Hermes 插件目录
ln -s $(pwd)/plugins/anp-agent ~/.hermes/plugins/anp-agent

# 在 ~/.hermes/config.yaml 中启用 anp 平台
cat >> ~/.hermes/config.yaml <<EOF
gateway:
  platforms:
    anp:
      extra:
        host: 0.0.0.0
        port: 8900
        hostname: localhost
        endpoint: http://localhost:8900
EOF

# 启动 Hermes gateway（测试环境需设置 ANP_ALLOW_ALL_USERS=1）
ANP_ALLOW_ALL_USERS=1 hermes run
```

### 本地启动

当前 OpenSpec 相关命令：

```bash
# 查看当前变更状态
openspec status --change create-anp-hermes-plugin

# 开始实现该变更
# /opsx:apply create-anp-hermes-plugin
```

### 接入 ANP 测试床

插件安装并重启 Gateway 后，继续在同一对话框中要求 LLM 完成以下测试床配置：

1. 设置环境变量（仅用于测试环境）：

   ```bash
   export ANP_ALLOW_ALL_USERS=1
   ```

2. 启动 DID 文档解析服务。插件默认会在 `http://{ANP_HOSTNAME}:{ANP_PORT}/.well-known/did.json` 公开自己的 `did:wba` 文档；若使用外部解析器，可配置：

   ```bash
   export ANP_DID_RESOLVER_BASE_URL=http://localhost:8900
   ```

3. 确保 `~/.hermes/config.yaml` 中已配置 LLM provider（真实 LLM 测试需要）。

完成以上步骤后，Hermes 即可作为 ANP 服务智能体被其他智能体发现和调用。

## 仓库结构

```
.
├── CLAUDE.md          # 本文件
├── openspec/          # OpenSpec 辅助规划工具目录（非项目建设内容）
│   ├── config.yaml
│   ├── specs/
│   └── changes/
│       └── create-anp-hermes-plugin/   # 当前进行中的变更
│           ├── proposal.md
│           ├── design.md
│           ├── tasks.md
│           └── specs/
└── .claude/           # Claude Code 自定义命令与技能
    ├── commands/
    └── skills/
```

## 本地开发环境

- **Hermes 源码**：`/home/peter/hermes-agent`
  - 实现插件时需要参考 `BasePlatformAdapter`、`MessageEvent`、`platform_registry`、`ctx.register_platform()` 等契约。
  - 插件代码必须零侵入 Hermes 核心，仅通过公开/稳定的插件接口与 Hermes 交互。
- **Hermes 程序**：本地已安装，并保持为最新版本。
  - 可用于 E2E 验证：启动 gateway 并加载 `anp-agent` 插件。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    ANP Demo Client                           │
│         （anp.openanp.RemoteAgent.discover）                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP + DID WBA 认证
┌───────────────────────────▼─────────────────────────────────┐
│                 Hermes ANP Platform Plugin                   │
│    ┌─────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│    │ /agent/ad.json │  │ /agent/interface.json │  │ POST /agent/rpc │  │
│    └─────────────┘  └─────────────────┘  └───────────────┘  │
│                          │                                   │
│                          ▼ Bridge (asyncio.Future)           │
│                   BasePlatformAdapter.handle_message         │
│                          │                                   │
│                          ▼                                   │
│                   Hermes Agent Core (LLM / skills / tools)   │
└─────────────────────────────────────────────────────────────┘
```

## 工作约定

- 本项目以应用代码为首要建设目标，`openspec/` 仅用于变更规划，不要在其中存放业务实现。
- 在引入技术栈前，先在本文件中更新对应的构建、测试与架构说明。
- 保持目录整洁：不要在根目录随意创建与项目目标无关的文件。
- 所有代码变更需服务于项目目标，并为 ANP 社区贡献做准备，保持高质量、高可测试性。

## 基本行为准则

> 来源：[multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md)

**权衡**：这些准则偏向谨慎而非速度。对于琐碎任务，请自行判断。

### 1. 编码前先思考

**不要假设。不要隐藏困惑。摆出权衡。**

实现前：
- 明确陈述你的假设。若不确定，请提问。
- 若存在多种理解，请全部列出——不要默默选择。
- 若存在更简单的方案，请说出来。必要时提出反对。
- 若某处不清楚，停下来，指出困惑点，提问。

### 2. 极简优先

**用最少代码解决问题。不要臆测。**
- 不实现超出需求的特性。
- 不为一次性代码做抽象。
- 不添加未被要求的“灵活性”或“可配置性”。
- 不处理不可能发生的场景的错误。
- 若 200 行能写成 50 行，就重写。

问自己：“资深工程师会觉得这过度设计吗？”若是，简化。

### 3. 精准改动

**只动必须动的。只清理自己制造的。**

编辑现有代码时：
- 不要“顺手改进”相邻代码、注释或格式。
- 不要重构没坏的东西。
- 匹配现有风格，即使你自己不会这么写。
- 若发现无关死代码，请指出——不要删除。

当你的改动产生孤儿代码时：
- 删除因你的改动而变得未使用的 import / 变量 / 函数。
- 不要删除既有的死代码，除非用户要求。

检验标准：**每一行改动都应能追溯到用户的请求。**

### 4. 目标驱动执行

**定义成功标准。循环直到验证通过。**

将任务转化为可验证的目标：
- “添加校验” → “为无效输入写测试，然后让它们通过”
- “修复 bug” → “写一个能复现 bug 的测试，然后让它通过”
- “重构 X” → “确保重构前后测试都通过”

多步骤任务先给出简要计划：
```
1. [步骤] → 验证：[检查]
2. [步骤] → 验证：[检查]
3. [步骤] → 验证：[检查]
```

明确的成功标准让你能独立迭代；模糊的标准（“让它跑起来”）需要反复澄清。

---

**这些准则生效的标志是**：diff 中不必要的改动更少、因过度设计导致的重写更少，并且在出错之前先提出问题而不是在出错之后。
