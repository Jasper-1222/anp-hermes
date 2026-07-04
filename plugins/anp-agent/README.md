# Hermes ANP Agent 平台插件

ANP（Agent Network Protocol）服务智能体 Hermes 平台插件参考实现。

## 功能

- 为 Hermes 生成并管理 ANP 原生 DID WBA 身份（`did:wba:`）。
- 暴露标准 ANP 端点：
  - `GET /agent/ad.json`：Agent Description
  - `GET /agent/interface.json`：OpenRPC 接口文档
  - `POST /agent/rpc`：JSON-RPC 2.0 调用入口
- 使用 DID WBA HTTP Message Signatures 验证调用方身份。
- 通过 asyncio Future 将 ANP 请求桥接到 Hermes 消息处理流程。

## 安装

```bash
pip install -e plugins/anp-agent/
```

或将 `plugins/anp-agent/` 复制到 `~/.hermes/plugins/anp-agent/`。

## 配置

在 `~/.hermes/config.yaml` 中启用 `anp` 平台：

```yaml
gateway:
  platforms:
    anp:
      extra:
        host: 0.0.0.0
        port: 8900
        hostname: localhost
        endpoint: http://localhost:8900
        data_dir: ~/.hermes/plugins/anp-agent/
        request_timeout: 60
        future_ttl: 120
```

环境变量优先级高于配置文件：

- `ANP_HOST`
- `ANP_PORT`
- `ANP_HOSTNAME`
- `ANP_ENDPOINT`
- `ANP_DATA_DIR`
- `ANP_REQUEST_TIMEOUT`
- `ANP_FUTURE_TTL`
- `ANP_ALLOW_ALL_USERS`（测试环境必需）

## 测试

```bash
cd plugins/anp-agent

# 单元测试与集成测试
python -m pytest tests/ -v

# 覆盖率检查（要求 ≥ 85%）
python -m pytest --cov=. --cov-fail-under=85 -q
```

### 端到端（E2E）测试

E2E 测试启动真实 Hermes gateway，并验证完整的 DID WBA 认证 → JSON-RPC → 响应链路。

```bash
cd plugins/anp-agent

# 阶段一：确定性 Echo E2E（本地 mock LLM，无需真实 API key）
python -m pytest tests/e2e/test_echo.py -v --run-e2e

# 阶段二：真实 LLM E2E（使用 ~/.hermes/config.yaml 中配置的 provider）
# 需要配置对应 provider 的 API key 环境变量，例如 DEEPSEEK_API_KEY
python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 阶段二：临时覆盖 provider（不修改 ~/.hermes/config.yaml）
# 例如使用 Kimi（Moonshot）Coding API
export ANP_E2E_LLM_PROVIDER="kimi"
export ANP_E2E_LLM_API="https://api.kimi.com/coding/v1"
export ANP_E2E_LLM_KEY_ENV="KIMI_API_KEY"
export KIMI_API_KEY="sk-..."
python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 同时运行两阶段 E2E 测试
python -m pytest tests/e2e/ -v --run-e2e --run-slow-e2e
```

前置条件：

- 本地已安装 Hermes 并可执行 `hermes`。
- 存在 `~/.hermes/config.yaml`，其中至少配置了 `model.provider`（真实 LLM 测试需要）。
- 阶段二测试会自动检查 provider 对应的环境变量，未设置时 `pytest.skip`。
- 可通过环境变量覆盖 provider，用于一次性测试不同 LLM：
  - `ANP_E2E_LLM_PROVIDER`：provider 名称
  - `ANP_E2E_LLM_API`：OpenAI 兼容 API base URL
  - `ANP_E2E_LLM_KEY_ENV`：读取 API key 的环境变量名

## 注意事项

- 测试环境必须设置 `ANP_ALLOW_ALL_USERS=1`，否则 Hermes allowlist 会拒绝新平台。
- 本期仅实现身份认证与明文 JSON-RPC 调用，不实现 AP2 支付与 E2EE 加密。
- DID 文档需要在生产环境真实可解析，测试时插件会公开自己的 DID 文档。

## 许可证

MIT
