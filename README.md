# anp-hermes

为 [ANP（Agent Network Protocol）](https://github.com/agent-network-protocol) 社区贡献的 Hermes 平台插件参考实现。

本项目通过 Hermes 的插件机制，让 Hermes 智能体能够作为 ANP 网络上的**服务智能体**被其他智能体发现和调用，且**零侵入 Hermes 核心代码**。

## 核心特性

- **ANP 原生身份**：自动生成并持久化管理 `did:wba:` DID WBA 身份，私钥本地保管。
- **DID WBA 认证**：使用 DID WBA HTTP Message Signatures 验证调用方身份。
- **标准 ANP 端点**：
  - `GET /agent/ad.json` — Agent Description
  - `GET /agent/interface.json` — OpenRPC 接口文档
  - `POST /agent/rpc` — JSON-RPC 2.0 调用入口
- **零侵入 Hermes**：仅通过 `BasePlatformAdapter`、`MessageEvent` 和 `ctx.register_platform()` 等公开插件接口与 Hermes 交互。
- **高质量测试**：45 项测试，覆盖率 ≥ 85%，`ruff` + `black` clean。

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Jasper-1222/anp-hermes.git
cd anp-hermes

# 安装插件
cd plugins/anp-agent
python -m pip install -e ".[test,dev]"

# 运行测试
python -m pytest tests/ -v
python -m pytest --cov=. --cov-fail-under=85 -q
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

插件启动后会自动生成 DID WBA 身份并监听 `http://localhost:8900`。

## 仓库结构

```
.
├── plugins/anp-agent/      # Hermes ANP 平台插件
│   ├── __init__.py         # 插件入口
│   ├── adapter.py          # Hermes 平台适配器
│   ├── auth.py             # DID WBA 认证
│   ├── bridge.py           # ANP JSON-RPC ↔ Hermes 桥接
│   ├── config.py           # 配置加载
│   ├── identity.py         # DID WBA 身份管理
│   ├── server.py           # aiohttp HTTP 端点
│   ├── tests/              # 单元与集成测试
│   └── README.md           # 插件详细说明
├── openspec/               # OpenSpec 规划产物
│   ├── specs/              # 归档后的 capability spec
│   └── changes/archive/    # 已归档变更
├── CLAUDE.md               # 项目开发指南
└── .github/workflows/ci.yml # CI 配置
```

## 设计约束

- 使用 ANP 原生 DID WBA 身份（`did:wba:`），不使用 `did:cn` 或其他 DID 方法。
- 不依赖 DTR、Portal、Mediator、OpenClaw 等外部基础设施。
- 仅依赖 ANP Python SDK（`anp>=0.8.8,<0.9.0`）和 Hermes 插件机制。
- 第一期仅实现身份认证 + JSON-RPC 调用；AP2 支付与 E2EE 加密放到后续。

## 贡献

欢迎为 ANP 社区贡献改进！请确保：

1. 测试通过：`python -m pytest tests/ -q --cov=. --cov-fail-under=85`
2. Lint 通过：`ruff check .` 和 `black --check .`
3. 提交信息使用中文，遵循项目约定。

## 许可证

MIT
