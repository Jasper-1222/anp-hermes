# ANP Hermes 当前实现综合分析报告

日期：2026-07-15
范围：`/home/peter/anp-hermes` 当前实现与 `/home/peter/agent-network-protocol` 本地 ANP 规范、SDK、示例对照  
状态：技术 Demo P0/P1 收口已完成

## 1. 总体结论

当前项目已经从“最小可运行链路”推进到 **ANP Hermes 社区参考实现候选**：

- 通过 Hermes 插件机制零侵入注册 `anp` 平台。
- 运行时代码已包化到 `plugins/anp-agent/anp_agent/`，根目录 `__init__.py` 只保留 Hermes 插件入口。
- 自动生成和加载 ANP 原生 DID WBA 身份，默认运行态目录为 `~/.hermes/data/anp-agent/`。
- 暴露当前已实现的 ANP 端点：
  - `GET /agent/ad.json`：Agent Description 直接发现入口。
  - `GET /.well-known/agent-descriptions`：主动发现 CollectionPage。
  - `GET /agent/interface.json`：OpenRPC 接口文档。
  - `POST /agent/rpc`：JSON-RPC 2.0 调用入口。
  - path DID 文档端点，例如 `/agent/e1_<fingerprint>/did.json`。
- 在 `/agent/rpc` 上执行 DID WBA HTTP Message Signatures 认证，并在成功认证后透传允许的 `Authentication-Info` 响应头。
- 支持 `chat`、`anp.get_capabilities` 和 ANP Core Binding `params.meta/body` envelope。
- 通过服务端内部 request id 隔离 pending Future，避免客户端 JSON-RPC `id` 冲突。
- 将超时、取消、handler 异常、pending 容量耗尽和工具调用错误映射为 JSON-RPC error，而不是伪装成成功 `result.response`。
- 可选暴露 allowlisted Hermes tools 为 `hermes.tool.<tool_name>` 方法；该能力默认关闭，并受 allowlist、denylist、caller DID 授权、参数校验、超时、结果大小和审计约束保护。
- 单元、集成、coverage、ruff/black、Echo E2E 已形成稳定本地验证矩阵。

因此，早期报告中的 P0/P1/P2 主要问题已经通过以下变更解决：

```text
reconcile-anp-spec-docs
protect-anp-runtime-secrets
return-authentication-info
harden-rpc-bridge
support-anp-core-binding
expand-agent-discovery
harden-test-harness
package-anp-plugin
productionize-did-resolver
expose-hermes-tools
```

当前剩余工作不再是”补齐最小协议链路”，而是保持技术 Demo 状态供社区体验。P2 和生产化能力不属于本轮完成条件。

## 2. 当前能力清单

### 2.1 身份与认证

- 使用 `did:wba:` DID WBA 身份，不使用 `did:cn` 或其他 DID 方法。
- DID 文档按 path DID 规则公开，例如：

  ```text
  did:wba:<host>:agent:e1_<fingerprint>
  → /agent/e1_<fingerprint>/did.json
  ```

- 私钥和 DID 文档默认写入 `~/.hermes/data/anp-agent/`。
- `ANP_DATA_DIR` 和 `gateway.platforms.anp.extra.data_dir` 仍可显式覆盖。
- `ANP_DID_RESOLVER_BASE_URL` 只允许 loopback base URL，用于本地开发、测试床和 E2E。
- 生产部署应让 DID Document 通过 DID WBA 默认 HTTPS 规则可解析。
- 认证失败使用结构化 JSON-RPC error code：`-32001` 到 `-32006`。
- 认证成功只透传允许的成功认证响应头，例如 `Authentication-Info`。

### 2.2 Discovery 与 OpenRPC

- `/agent/ad.json` 保留直接发现兼容字段，并补充 ANP Agent Description 基础字段。
- `/.well-known/agent-descriptions` 返回 JSON-LD CollectionPage，item 的 `@id` 指向 `/agent/ad.json`。
- `/agent/interface.json` 始终声明当前基础方法：`chat` 和 `anp.get_capabilities`。
- 仅当 tool RPC 显式启用且存在 allowlisted 工具时，OpenRPC 才声明 `hermes.tool.*` 方法。
- 未实现的 Direct、Group、E2EE、DTR、Portal、Mediator 不会被声明。

### 2.3 JSON-RPC 与 Core Binding

- `/agent/rpc` 只接收单个 JSON-RPC 2.0 请求对象。
- 拒绝 batch、notification、无效 `jsonrpc`、非字符串或空字符串 `id`、无效 `method` 和无效 `params`。
- 成功 `chat` 返回：

  ```json
  {"jsonrpc":"2.0","result":{"response":"..."},"id":"..."}
  ```

- `anp.get_capabilities` 返回 service DID、supported profiles、supported security profiles、limits 和 supported content types。
- 支持 legacy `params.message` 与 Core Binding `params.body.message`。
- bridge 失败返回 JSON-RPC error，不返回成功 `result.response`。

### 2.4 Hermes tool RPC

- `tool_rpc` 默认关闭。
- 开启后仍必须配置 caller DID 授权和工具 allowlist。
- 配置项包括：
  - `enabled`
  - `allowed_dids`
  - `allowed_tools`
  - `allowed_toolsets`
  - `denied_tools`
  - `timeout_seconds`
  - `max_result_bytes`
- denylist 优先于 allowlist。
- 内置高风险 denylist 默认拒绝 shell、代码执行、文件写入、skill 管理、浏览器自动化、外部发布等工具。
- 未授权或未暴露工具按 JSON-RPC `-32601` 返回，避免泄露工具存在性。
- 参数无效返回 `-32602`。
- 执行失败、超时、取消、结果过大返回安全的 `-32603`。
- 工具执行器支持注入不记录完整参数/结果的安全审计回调；当前默认 server 未配置 audit sink，因此默认不输出或持久化审计事件。持久化审计不属于本技术 Demo 的当前范围。

### 2.5 包化与发布结构

插件 release zip 根目录应包含：

```text
plugin.yaml
__init__.py
README.md
pyproject.toml
anp_agent/
```

不应包含运行态 DID/PEM、缓存、coverage 或备份文件。

## 3. 当前验证基线

技术 Demo 本地验证矩阵：

```bash
# OpenSpec 全量校验
openspec validate --all

# 仓库根级依赖与发布测试
python3 -m pytest tests/ -q

# ANP 调用端 skill 测试与 lint
python3 -m pytest clients/anp-client/tests/ -q
ruff check clients/anp-client
black --check clients/anp-client

# 插件普通测试与覆盖率
cd plugins/anp-agent
python3 -m pytest tests/ -q
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q

# Lint 与格式化（插件）
ruff check .
black --check .

# 确定性 Echo E2E（本地 mock LLM，无真实 API key）
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e

# 根级 lint 与打包
ruff check scripts tests
black --check scripts tests
python3 scripts/package_anp_release.py
```

真实 LLM E2E 是条件验证：

```bash
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```

该测试依赖 `~/.hermes/config.yaml` 中的 provider 和对应 API key。本轮未重新运行真实 LLM 测试。

## 4. 仍需谨慎的边界

### 4.1 Bearer token 后续请求完整验收

当前实现已经支持成功认证时返回 `Authentication-Info`。完整验收不属于本技术 Demo 范围。

### 4.2 ANP SDK resolver injection 上游协作

当前 resolver override 已收紧为本地 loopback 用途，生产默认走 DID WBA HTTPS 解析。上游协作不属于本技术 Demo 范围。

### 4.3 生产部署指南

当前 README 已说明本地和测试床配置。生产部署指南不属于本技术 Demo 范围。

### 4.4 限流与审计持久化

tool RPC 已有默认关闭、授权、错误映射和审计回调注入点。限流和持久化审计不属于本技术 Demo 范围。

### 4.5 社区示例客户端

社区示例客户端不属于本技术 Demo 范围。

## 5. 当前不实施范围

本项目当前以技术 Demo 为完成目标。生产部署、Bearer 后续请求、per-DID 限流、持久化审计、resolver 上游改造、跨机器 DID 托管、AP2 和 E2EE 保留为可选后续主题，不属于本轮完成条件。
   - 完整验收 DID WBA `Authentication-Info` token 后续请求流程。
3. `upstream-anp-resolver-injection`
   - 调研并准备向 ANP Python SDK 贡献 resolver injection 能力。
4. `add-rate-limit-and-audit-sinks`
   - 为 `/agent/rpc` 和 tool RPC 增加 per-DID 限流与审计持久化。
5. `add-community-client-examples`
   - 增加最小客户端示例和 README 链接，方便社区复现。

## 6. 最终评价

项目方向正确，且前十个 OpenSpec 变更已经把早期发现的协议、并发、安全、测试、包化、resolver 与工具暴露问题逐步收敛。当前代码和文档已经接近社区参考实现候选状态。

项目方向正确，且前 18 个 OpenSpec 变更已经把早期发现的协议、并发、安全、测试、包化、resolver 与工具暴露问题逐步收敛。当前代码和文档已经达到技术 Demo 可公开、可验证状态。项目可保持当前状态供社区体验；后续新增能力应继续保持 OpenSpec 小步推进。