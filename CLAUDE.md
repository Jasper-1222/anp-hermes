# CLAUDE.md

This file provides guidance to Claude Code when working in this repository. Keep it project-specific; global coding behavior lives in `~/.claude/CLAUDE.md`.

## 项目目标

本项目目标是为 ANP（Agent Network Protocol）社区贡献一个高质量 Hermes 接入参考实现：通过 Hermes 插件机制，让 Hermes 智能体作为 ANP 网络上的服务智能体被发现和调用。本轮完成技术 Demo P0/P1 收口；不以生产部署、限流、持久化审计或跨机器 DID 托管为目标。

硬约束：
- 使用 ANP 原生 DID WBA 身份（`did:wba:`）。
- 仅使用 ANP Python SDK 与 Hermes 插件机制。
- 插件必须零侵入 Hermes 核心代码，便于社区贡献和独立发布。
- 第一期仅实现身份认证 + JSON-RPC 调用；AP2 支付和 E2EE 加密延后。
- Hermes tool RPC 是默认关闭的可选能力，只能在显式 allowlist/denylist 与 caller DID 授权后暴露低风险工具。

## 官方语言

本项目官方语言为中文。文档、代码注释、业务语义命名、提交信息、Issue/PR 描述等均应使用中文。

## 常用命令

```bash
# 仓库根级依赖与发布测试
python3 -m pytest tests/ -q

# 插件开发目录
cd plugins/anp-agent

# 安装插件及测试/开发依赖
python3 -m pip install -e ".[test,dev]"

# 单元与集成测试
python3 -m pytest tests/ -q
python3 -m pytest tests/test_server.py -v

# 覆盖率门槛：≥ 85%
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q

# 格式与 lint（根/客户端与插件分开运行）
ruff check plugins/anp-agent clients/anp-client
cd plugins/anp-agent && black --check .
black --check clients/anp-client

# E2E：本地 mock LLM，无真实 API key
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e

# E2E：真实 LLM，使用 ~/.hermes/config.yaml 中的 provider
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# E2E：临时覆盖 provider，不修改 ~/.hermes/config.yaml
ANP_E2E_LLM_PROVIDER="kimi" \
ANP_E2E_LLM_API="https://api.kimi.com/coding/v1" \
ANP_E2E_LLM_KEY_ENV="KIMI_API_KEY" \
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# ANP 调用端 skill
python3 -m pytest clients/anp-client/tests/ -q
ruff check clients/anp-client
black --check clients/anp-client

# 构建版本化包与稳定别名
python3 scripts/package_anp_release.py
```

## OpenSpec 当前状态

- `close-demo-readiness` 之前共有 18 个 OpenSpec 变更完成、同步并归档。
- 当前 active changes 应为空；新工作应先创建新的 OpenSpec change。
- main specs 当前包含 16 个 capability specs。
- 常用命令：

```bash
openspec list
openspec status --change <change-id>
openspec validate --all
# /opsx:apply <change-id>
# /opsx:sync <change-id>
# /opsx:archive <change-id>
```

上下文恢复优先读取：
1. `docs/anp-hermes-openspec-execution-state.md`
2. `docs/anp-hermes-openspec-roadmap.md`
3. `docs/anp-hermes-current-implementation-analysis.md`

## 本地开发环境

- Hermes 源码：`/home/peter/hermes-agent`
  - 参考 `BasePlatformAdapter`、`MessageEvent`、`platform_registry`、`ctx.register_platform()`。
  - 插件代码必须只通过公开/稳定插件接口与 Hermes 交互。
- Hermes 程序：本地已安装并保持最新，可用于 E2E 验证。
- ANP 协议仓库：`/home/peter/agent-network-protocol`
  - 查询 ANP 协议细节时优先使用本地仓库，无需再拉 GitHub。

## 仓库结构

```text
.
├── CLAUDE.md                 # 本文件
├── README.md                 # 项目总览与快速开始
├── clients/anp-client/       # ANP 调用端 skill：身份、DID 服务、发现与签名 chat
├── scripts/                  # SDK 验证与 plugin/client 发布包构建
├── tests/                    # 根级依赖和发布包测试
├── docs/                     # 当前实现分析、OpenSpec 路线图与执行状态
├── openspec/                 # OpenSpec 辅助规划工具目录（非业务实现）
│   ├── config.yaml
│   ├── specs/                # 当前 capability spec
│   └── changes/              # 活跃变更与 archive/ 已归档变更
└── plugins/anp-agent/        # Hermes ANP 平台插件
    ├── __init__.py           # Hermes 插件入口
    ├── plugin.yaml           # Hermes 插件元数据
    ├── pyproject.toml        # Python 包与测试配置
    ├── anp_agent/            # 插件运行时 Python 包
    │   ├── adapter.py        # Hermes 平台适配器
    │   ├── auth.py           # DID WBA 认证
    │   ├── bridge.py         # ANP JSON-RPC ↔ Hermes 桥接
    │   ├── config.py         # 配置加载
    │   ├── identity.py       # DID WBA 身份管理
    │   ├── server.py         # aiohttp HTTP 端点
    │   └── tools.py          # 可选 Hermes tool RPC 策略、授权、参数校验与执行
    └── tests/                # 单元、集成与 E2E 测试
```

## 架构速览

```text
ANP Client / RemoteAgent.discover
        │ HTTP + DID WBA 认证
        ▼
Hermes ANP Platform Plugin
  ├─ GET /agent/ad.json
  ├─ GET /.well-known/agent-descriptions
  ├─ GET /agent/interface.json
  └─ POST /agent/rpc
        │ JSON-RPC bridge / asyncio.Future
        ▼
Hermes Agent Core（LLM / skills / tools）
```

## 项目特有 gotchas

- `openspec/` 只存变更规划和 capability specs，不存业务实现。
- DID 文档与私钥 PEM 默认写入 `~/.hermes/data/anp-agent/`；不要写入插件安装目录或提交到仓库。
- `ANP_DID_RESOLVER_BASE_URL` 仅用于本地开发、测试床与 E2E，只接受 loopback base URL。生产部署应让 DID WBA 默认 HTTPS 规则解析到公开 `https://{domain}/agent/e1_<fingerprint>/did.json`。
- 测试环境可用 `ANP_ALLOW_ALL_USERS=1`；公开部署不要依赖该开关。
- tool RPC 默认关闭。不要默认暴露 shell、代码执行、文件写入、skill 管理、浏览器自动化、外部发布等高风险工具。
- 通过 Hermes 对话框安装插件时，release zip 根目录必须直接包含 `plugin.yaml`、`__init__.py` 与 `anp_agent/`。
- 引入新技术栈前，先更新本文件中的命令、架构或 gotchas。
