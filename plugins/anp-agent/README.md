# Hermes ANP Agent 平台插件

ANP（Agent Network Protocol）服务智能体 Hermes 平台插件参考实现。

## 功能

- 为 Hermes 生成并管理 ANP 原生 DID WBA 身份（`did:wba:`）。
- 暴露标准 ANP 端点：
  - `GET /agent/ad.json`：Agent Description（直接发现入口）
  - `GET /.well-known/agent-descriptions`：JSON-LD CollectionPage（主动发现入口，索引到 `/agent/ad.json`）
  - `GET /agent/interface.json`：OpenRPC 接口文档
  - `POST /agent/rpc`：JSON-RPC 2.0 调用入口
- 使用 DID WBA HTTP Message Signatures 验证调用方身份，并在成功认证后通过 `Authentication-Info` 返回认证信息。
- 通过 asyncio Future 将 ANP 请求桥接到 Hermes 消息处理流程。
- 可选暴露 allowlisted Hermes tools 为 `hermes.tool.<tool_name>` JSON-RPC 方法；该能力默认关闭，且内置拒绝高风险工具。

## 安装

### 对话框安装（发布 Release 后）

仓库创建 GitHub Release 并上传稳定资产 `anp-agent.zip` 后，可以在 Hermes 对话框中发送：

```text
安装插件 https://github.com/Jasper-1222/anp-hermes/releases/latest/download/anp-agent.zip
```

当前源码仓库尚未创建 Release；本地体验请使用下方手动安装，或运行仓库根 `python3 scripts/package_anp_release.py` 生成 `dist/anp-agent.zip`。

1. 下载 `anp-agent.zip`。
2. 检查 zip 内包含 `plugin.yaml`、`__init__.py` 与 `anp_agent/`。
3. 解压到 `~/.hermes/plugins/anp-agent/`；若 zip 内部包含顶层目录，需将其内容直接移入 `~/.hermes/plugins/anp-agent/`，确保 `plugin.yaml`、`__init__.py` 与 `anp_agent/` 位于该目录根下。
4. 在 `~/.hermes/config.yaml` 中启用 `anp-agent` 插件，并添加 `gateway.platforms.anp` 配置（见下方示例）。
5. 重启 Hermes gateway。
6. 报告成功或遇到的错误。

> 提示：如果 zip 托管位置不同，只需把 URL 替换为实际下载地址。

### 手动安装

```bash
pip install -e plugins/anp-agent/
```

或将 `plugins/anp-agent/` 复制到 `~/.hermes/plugins/anp-agent/`。

## 配置

插件运行时代码位于 `anp_agent/` Python 包中，Hermes 仍通过插件根目录的 `plugin.yaml` 与 `__init__.py:register` 加载平台。发布 zip 解压到 `~/.hermes/plugins/anp-agent/` 后，插件根目录应直接包含：

```text
plugin.yaml
__init__.py
README.md
pyproject.toml
anp_agent/
```

不要将 `did.json`、`*.pem`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`.coverage` 或备份文件打入发布 zip。

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
        # 可选：默认使用 ~/.hermes/data/anp-agent/
        # data_dir: ~/.hermes/data/anp-agent/
        request_timeout: 60
        future_ttl: 120
        # 可选：默认关闭；仅显式 allowlist 后暴露低风险 Hermes tools
        tool_rpc:
          enabled: false
          allowed_dids: []
          allowed_tools: []
          allowed_toolsets: []
          denied_tools: []
          timeout_seconds: 30
          max_result_bytes: 65536
```

环境变量优先级高于配置文件：

- `ANP_HOST`
- `ANP_PORT`
- `ANP_HOSTNAME`
- `ANP_ENDPOINT`
- `ANP_DATA_DIR`（覆盖 DID 文档与私钥 PEM 的持久化目录；未设置时默认 `~/.hermes/data/anp-agent/`）
- `ANP_REQUEST_TIMEOUT`
- `ANP_FUTURE_TTL`
- `ANP_DID_RESOLVE_TIMEOUT`（DID 文档解析超时，默认 10 秒；非法、零值、负值回退默认值，超大值限制到 60 秒）
- `ANP_DID_RESOLVER_BASE_URL`（仅用于本地开发、测试床与 E2E 的 loopback DID 文档服务器，例如 `http://127.0.0.1:18900`；生产环境不要依赖该变量）
- `ANP_ALLOW_ALL_USERS`（本地测试推荐 `1`，公开部署不要依赖该开关）

## 本地安装包验证推荐配置

通过 Hermes 对话框安装 plugin zip 后，本地测试建议在 Hermes gateway 启动前设置：

```bash
export ANP_ALLOW_ALL_USERS=1
export ANP_DID_RESOLVER_BASE_URL=http://127.0.0.1:18900
```

`ANP_ALLOW_ALL_USERS=1` 只建议用于本地验证，可避免 OpenClaw/anp-client 每次生成临时 DID 后触发配对授权。公开部署请关闭该开关，并使用 `ANP_ALLOWED_USERS` 配置允许的调用方 DID。

`ANP_DID_RESOLVER_BASE_URL` 让服务端在本地测试时通过 OpenClaw/anp-client 的 `serve-did` 解析调用方 DID 文档。该变量在 ANP 认证器初始化时读取，因此运行中的 Hermes gateway 修改环境变量不会生效，需要重启 gateway。

默认情况下，运行态身份文件会写入 `~/.hermes/data/anp-agent/`，避免与插件源码或安装目录混放。若旧环境已经在其他目录生成 `did.json` 与 `private_key.pem`，可通过 `data_dir` 或 `ANP_DATA_DIR` 显式继续使用旧目录，也可在停止 Gateway 后手动迁移到新目录。本插件不会自动删除、移动或覆盖你本地已有的密钥文件。

### Hermes tools RPC（可选）

`tool_rpc` 默认关闭。开启后，插件会把通过策略校验的 Hermes tool 暴露为 OpenRPC 方法：

```text
hermes.tool.<tool_name>
```

安全边界：

- 必须显式设置 `enabled: true`。
- 必须配置 `allowed_dids`，只有这些 DID WBA 调用方可以调用工具。
- 必须配置 `allowed_tools` 或 `allowed_toolsets`；插件不会自动暴露 Hermes 当前可见的全部工具。
- `denied_tools` 和内置高风险 denylist 优先于 allowlist。
- 默认拒绝 shell、代码执行、文件写入、skill 管理、浏览器自动化、外部发布等高风险工具。
- 工具调用失败、超时、参数无效或结果过大时返回 JSON-RPC error；失败响应不附带成功认证 `Authentication-Info`。

示例：

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

生产环境建议从只读、低风险工具开始逐项 allowlist；不要把 `ANP_ALLOW_ALL_USERS=1` 与 tool RPC 组合为公开服务配置。

## 接入 ANP 测试床

插件安装并重启 Gateway 后，继续在同一对话框中要求 LLM 完成以下测试床配置：

1. 设置环境变量（仅用于测试环境）：

   ```bash
   export ANP_ALLOW_ALL_USERS=1
   ```

2. 启动本地 loopback DID 文档解析服务。插件默认生成 DID WBA path DID，例如 `did:wba:{ANP_HOSTNAME}:agent:e1_<fingerprint>`，并在 `http://{ANP_HOSTNAME}:{ANP_PORT}/agent/e1_<fingerprint>/did.json` 公开 DID 文档；本地测试床可配置：

   ```bash
   export ANP_DID_RESOLVER_BASE_URL=http://localhost:8900
   ```

   该变量只接受 loopback base URL（如 `localhost`、`127.0.0.1`、`::1`），用于本地开发、测试床与 E2E。生产部署不要依赖该 override；应让服务 DID 可通过 DID WBA 默认 HTTPS 规则解析，例如 `did:wba:example.com:agent:e1_<fingerprint>` 对应 `https://example.com/agent/e1_<fingerprint>/did.json`。

3. 确保 `~/.hermes/config.yaml` 中已配置 LLM provider（真实 LLM 测试需要）。

完成以上步骤后，Hermes 即可作为 ANP 服务智能体被其他智能体发现和调用。

## 发现端点

插件提供两个公开发现入口：

- `GET /agent/ad.json`：直接返回当前 Hermes ANP 服务智能体的 Agent Description，适合已知 AD URL 的直接发现流程。
- `GET /.well-known/agent-descriptions`：返回 JSON-LD `CollectionPage`，其中 `items` 包含指向 `/agent/ad.json` 的轻量索引项，适合按域名主动发现公开智能体。

`/.well-known/agent-descriptions` 不内嵌完整 Agent Description；调用方应继续读取 item 的 `@id` 指向的 `/agent/ad.json` 获取完整描述。

## 测试

普通测试会通过根发布脚本在临时目录生成并检查 zip，不要求源码目录预先存在 ignored `anp-agent.zip`。从仓库根运行完整打包可得到版本化文件和稳定别名：

```bash
python3 scripts/package_anp_release.py
```

```bash
cd plugins/anp-agent

# 单元测试与集成测试
python3 -m pytest tests/ -v

# 覆盖率检查（要求 ≥ 85%）
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

### 端到端（E2E）测试

E2E 测试启动真实 Hermes gateway，并验证完整的 DID WBA 认证 → JSON-RPC → 响应链路。

```bash
cd plugins/anp-agent

# 阶段一：确定性 Echo E2E（本地 mock LLM，无需真实 API key，不依赖真实 ~/.hermes/config.yaml）
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e

# 阶段二：真实 LLM E2E（使用 ~/.hermes/config.yaml 中配置的 provider）
# 需要配置对应 provider 的 API key 环境变量，例如 DEEPSEEK_API_KEY
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 阶段二：临时覆盖 provider（不修改 ~/.hermes/config.yaml）
# 例如使用 Kimi（Moonshot）Coding API
export ANP_E2E_LLM_PROVIDER="kimi"
export ANP_E2E_LLM_API="https://api.kimi.com/coding/v1"
export ANP_E2E_LLM_KEY_ENV="KIMI_API_KEY"
export KIMI_API_KEY="sk-..."
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e

# 同时运行两阶段 E2E 测试
python3 -m pytest tests/e2e/ -v --run-e2e --run-slow-e2e
```

前置条件：

- 本地已安装 Hermes 并可执行 `hermes`。
- 阶段一 Echo E2E 使用临时 `HOME` / `HERMES_HOME`、临时 Hermes config 与本地 mock LLM；无需真实 API key，也不读取或修改用户真实 `~/.hermes/config.yaml`。
- 阶段二真实 LLM E2E 仅在同时传入 `--run-e2e --run-slow-e2e` 后运行；缺少 `model.provider` 或对应 API key 时会在启动 Gateway 前 `pytest.skip`。
- 可通过环境变量覆盖 provider，用于一次性测试不同 LLM：
  - `ANP_E2E_LLM_PROVIDER`：provider 名称
  - `ANP_E2E_LLM_API`：OpenAI 兼容 API base URL
  - `ANP_E2E_LLM_KEY_ENV`：读取 API key 的环境变量名

## 注意事项

- 测试环境必须设置 `ANP_ALLOW_ALL_USERS=1`，否则 Hermes allowlist 会拒绝新平台。
- 运行态身份文件默认写入 `~/.hermes/data/anp-agent/`；不要将 `did.json`、`private_key.pem` 或其他 PEM 私钥提交到仓库。
- 当前实现覆盖最小 ANP/OpenANP 链路：DID WBA 身份、DID WBA HTTP Message Signatures 认证、成功认证 `Authentication-Info` 响应头、`/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json`、`/agent/rpc`、`anp.get_capabilities` 与通用 `chat` 方法。
- 本期仅实现身份认证与明文 JSON-RPC 调用，不实现 AP2 支付与 E2EE 加密。
- DID 文档需要在生产环境真实可解析；当前默认 DID 为 path DID，测试时插件会在对应 path DID 路径公开自己的 DID 文档。

## 许可证

MIT
