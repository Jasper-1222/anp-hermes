# anp-hermes

为 [ANP（Agent Network Protocol）](https://github.com/agent-network-protocol) 社区贡献的 Hermes 平台插件参考实现。

本项目通过 Hermes 的插件机制，让 Hermes 智能体能够作为 ANP 网络上的**服务智能体**被其他智能体发现和调用，且**零侵入 Hermes 核心代码**。

## 核心特性

- **ANP 原生身份**：自动生成并持久化管理 `did:wba:` DID WBA 身份，私钥本地保管。
- **DID WBA 认证**：使用 DID WBA HTTP Message Signatures 验证调用方身份，并在成功认证后通过 `Authentication-Info` 返回认证信息。
- **标准 ANP 端点**：
  - `GET /agent/ad.json` — Agent Description（直接发现入口）
  - `GET /.well-known/agent-descriptions` — JSON-LD CollectionPage（主动发现入口）
  - `GET /agent/interface.json` — OpenRPC 接口文档
  - `POST /agent/rpc` — JSON-RPC 2.0 调用入口
- **可选 Hermes tools RPC**：默认关闭；仅在显式配置 allowlist、denylist 与 caller DID 授权后，通过 `hermes.tool.<tool_name>` 暴露低风险 Hermes 工具。
- **零侵入 Hermes**：仅通过 `BasePlatformAdapter`、`MessageEvent` 和 `ctx.register_platform()` 等公开插件接口与 Hermes 交互。
- **高质量测试**：单元、集成与 E2E 测试覆盖核心协议路径，覆盖率 ≥ 85%，`ruff` + `black` clean。

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Jasper-1222/anp-hermes.git
cd anp-hermes

# 安装插件
cd plugins/anp-agent
python3 -m pip install -e ".[test,dev]"

# 运行测试
python3 -m pytest tests/ -v
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

## 发布打包

```bash
python3 scripts/package_anp_release.py
```

脚本会生成并校验：

- `dist/anp-agent-plugin-0.1.0.zip`
- `dist/anp-client-skill-0.1.0.zip`

发布包只包含 allowlist 文件，并会拒绝打包 DID 文档、私钥、缓存、pyc、本机绝对路径和真实私钥块。

## 测试

```bash
cd plugins/anp-agent

# 单元测试与集成测试
python3 -m pytest tests/ -v

# 覆盖率检查（要求 ≥ 85%）
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q

# 阶段一：确定性 Echo E2E（本地 mock LLM，无需真实 API key，不依赖真实 ~/.hermes/config.yaml）
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e

# 阶段二：真实 LLM E2E（慢速，可选）
# 需要 ~/.hermes/config.yaml 中配置 model.provider，并设置对应 provider 的 API key 环境变量
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 也可临时覆盖 provider，不修改 ~/.hermes/config.yaml
ANP_E2E_LLM_PROVIDER="kimi" \
ANP_E2E_LLM_API="https://api.kimi.com/coding/v1" \
ANP_E2E_LLM_KEY_ENV="KIMI_API_KEY" \
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```

## 本地启动 Hermes + ANP 插件

```bash
# 将插件链接到 Hermes 插件目录
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

# 启动 gateway（测试环境需设置 ANP_ALLOW_ALL_USERS=1）
ANP_ALLOW_ALL_USERS=1 hermes run
```

插件启动后会自动生成 DID WBA 身份并监听 `http://localhost:8900`。默认情况下，DID 文档与私钥 PEM 写入 `~/.hermes/data/anp-agent/`；如需复用旧身份，可在 `gateway.platforms.anp.extra.data_dir` 或 `ANP_DATA_DIR` 中显式指定旧目录。

如需让 ANP 调用方直接调用 Hermes tools，可在 `gateway.platforms.anp.extra.tool_rpc` 中显式开启。该能力默认关闭，且必须配置 caller DID 与工具 allowlist；内置 denylist 会拒绝 shell、代码执行、文件写入、skill 管理、浏览器自动化和外部发布等高风险工具：

```yaml
gateway:
  platforms:
    anp:
      extra:
        tool_rpc:
          enabled: true
          allowed_dids:
            - did:wba:example.com:agent:caller
          allowed_tools:
            - skills_list
          denied_tools:
            - skill_manage
          timeout_seconds: 30
          max_result_bytes: 65536
```

生产部署时，不应依赖 `ANP_DID_RESOLVER_BASE_URL` 才能解析服务 DID。DID WBA 默认解析规则会把 `did:wba:{domain}:agent:e1_<fingerprint>` 解析到 `https://{domain}/agent/e1_<fingerprint>/did.json`；因此生产环境应通过 HTTPS 反向代理或标准端口让该 path 可公开访问。`ANP_DID_RESOLVER_BASE_URL` 仅用于本地开发、测试床和 E2E 的 loopback DID 文档服务器。

> 运行态身份文件（如 `did.json`、`*.pem`）不应放入源码目录。本仓库会忽略 `plugins/anp-agent/` 下误生成的身份文件，但不会自动删除或迁移你本地已有的密钥文件；如需清理或迁移，请先确认目标目录与备份。

## 仓库结构

```
.
├── plugins/anp-agent/      # Hermes ANP 平台插件
│   ├── __init__.py         # Hermes 插件入口（注册 anp 平台）
│   ├── plugin.yaml         # Hermes 插件元数据
│   ├── pyproject.toml      # Python 包与测试配置
│   ├── anp_agent/          # 插件运行时 Python 包
│   │   ├── adapter.py      # Hermes 平台适配器
│   │   ├── auth.py         # DID WBA 认证
│   │   ├── bridge.py       # ANP JSON-RPC ↔ Hermes 桥接
│   │   ├── config.py       # 配置加载
│   │   ├── identity.py     # DID WBA 身份管理
│   │   ├── server.py       # aiohttp HTTP 端点
│   │   └── tools.py        # 可选 Hermes tool RPC 策略与执行
│   ├── tests/              # 单元、集成与 E2E 测试
│   └── README.md           # 插件详细说明
├── docs/                    # 当前实现分析、OpenSpec 路线图与执行状态
├── openspec/               # OpenSpec 规划产物
│   ├── specs/              # 当前 capability spec
│   └── changes/            # 活跃变更与 archive/ 已归档变更
├── CLAUDE.md               # 项目开发指南
└── .github/workflows/ci.yml # CI 配置
```

## 设计约束

- 使用 ANP 原生 DID WBA 身份（`did:wba:`）。
- 不依赖 DTR、Portal、Mediator、OpenClaw 等外部基础设施。
- 仅依赖 ANP Python SDK（`anp>=0.8.8,<0.9.0`）和 Hermes 插件机制。
- 第一期仅实现身份认证 + JSON-RPC 调用；AP2 支付与 E2EE 加密放到后续。
- 当前实现覆盖最小 ANP/OpenANP 链路；已支持 `anp.get_capabilities` 与 `/.well-known/agent-descriptions`，并已完成插件运行时代码包化和 DID resolver 生产边界收敛。Hermes tools RPC 已实现为默认关闭的可选能力，必须通过 allowlist/denylist 与 caller DID 授权显式开启。

## 贡献

欢迎为 ANP 社区贡献改进！请确保：

1. 测试通过：`python3 -m pytest tests/ -q` 与 `python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q`
2. Lint 通过：`ruff check .` 和 `black --check .`
3. 提交信息使用中文，遵循项目约定。

## 许可证

MIT
