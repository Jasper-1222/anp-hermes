# ANP Hermes OpenSpec 执行状态

日期：2026-07-08

## 当前状态

前十个 OpenSpec 变更已完成并归档：

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

当前 active change：

```text
review-community-readiness
```

状态：前十个路线图变更已完成并归档。当前正在执行 `review-community-readiness` 收尾审计变更，用于更新分析报告、路线图和文档一致性，并运行社区就绪验证矩阵。`expose-hermes-tools` 已完成实现、验证、main specs 同步与归档，归档目录为 `openspec/changes/archive/2026-07-08-expose-hermes-tools/`。

## 用户约定

- 后续使用 opsx 技能顺序推进：`/opsx:propose` → `/opsx:apply` → 验证 → `/opsx:archive`。
- OpenSpec CLI 可由助手按技能要求直接执行。
- 所有文档、规格、提交信息继续使用中文。

## 当前 active change

```text
review-community-readiness
```

状态：`review-community-readiness` apply 进行中。目标是把文档从“执行中路线图”收口为“社区参考实现候选”状态，复核 README、插件 README、CLAUDE.md、main specs 与执行状态文档，并记录社区就绪验证矩阵。

## 已完成

- [x] 输出当前实现综合分析报告：`docs/anp-hermes-current-implementation-analysis.md`
- [x] 保存长期路线图：`docs/anp-hermes-openspec-roadmap.md`
- [x] 初始化执行状态文件：`docs/anp-hermes-openspec-execution-state.md`
- [x] 创建 `reconcile-anp-spec-docs` proposal/design/tasks/spec deltas
- [x] 应用 `reconcile-anp-spec-docs` 文档与规格清理
- [x] 归档 `reconcile-anp-spec-docs`
- [x] 创建 `protect-anp-runtime-secrets` proposal/design/tasks/spec deltas
- [x] 应用 `protect-anp-runtime-secrets` 运行态密钥保护变更
- [x] 同步并归档 `protect-anp-runtime-secrets`
- [x] 创建 `return-authentication-info` proposal/design/tasks/spec deltas
- [x] 应用 `return-authentication-info` 成功认证响应头变更
- [x] 同步并归档 `return-authentication-info`
- [x] 创建 `harden-rpc-bridge` proposal/design/tasks/spec deltas
- [x] 应用 `harden-rpc-bridge` RPC bridge 加固变更
- [x] 同步并归档 `harden-rpc-bridge`
- [x] 创建 `support-anp-core-binding` proposal/design/tasks/spec deltas
- [x] 应用 `support-anp-core-binding` ANP Core Binding 兼容变更
- [x] 同步并归档 `support-anp-core-binding`
- [x] 创建 `expand-agent-discovery` proposal/design/tasks/spec deltas
- [x] 应用 `expand-agent-discovery` 主动发现增强变更
- [x] 同步并归档 `expand-agent-discovery`
- [x] 创建 `harden-test-harness` proposal/design/tasks/spec deltas
- [x] 应用并验证 `harden-test-harness` 测试体系加固变更
- [x] 同步并归档 `harden-test-harness`
- [x] 创建 `package-anp-plugin` proposal/design/tasks/spec deltas
- [x] 应用并验证 `package-anp-plugin` 插件包化变更
- [x] 同步并归档 `package-anp-plugin`
- [x] 创建 `productionize-did-resolver` proposal/design/tasks/spec deltas
- [x] 应用并验证 `productionize-did-resolver` DID resolver 生产边界变更
- [x] 同步并归档 `productionize-did-resolver`
- [x] 创建 `expose-hermes-tools` proposal/design/tasks/spec deltas
- [x] 应用并验证 `expose-hermes-tools` Hermes tools 安全暴露变更
- [x] 同步并归档 `expose-hermes-tools`

## `reconcile-anp-spec-docs` 完成内容

- [x] 清理 OpenSpec active/archive 状态。
- [x] 修正 DID 文档路径说明。
- [x] 修正 JSON-RPC result shape 说明。
- [x] 明确当前阶段不强制要求 `agent.json`。
- [x] 明确当前阶段不强制要求 `AuthenticationError.cause`。
- [x] 补全 main specs 的 `Purpose`。
- [x] 修正 README / CLAUDE 中过期 OpenSpec 状态说明。

## `protect-anp-runtime-secrets` 完成内容

- [x] 将 `plugins/anp-agent/did.json`、`plugins/anp-agent/*.pem`、临时文件与备份文件加入 `.gitignore`。
- [x] 将默认 `data_dir` 调整为 `~/.hermes/data/anp-agent/`，避免默认写入插件源码或安装目录。
- [x] 保持 `ANP_DATA_DIR` > `extra.data_dir` > 默认值的配置优先级。
- [x] 增加配置测试，覆盖默认目录、配置文件覆盖与环境变量覆盖。
- [x] 增加身份测试，确认显式目录、损坏备份与私钥权限 `0o600` 不依赖插件源码目录。
- [x] 更新根 README、插件 README 与 CLAUDE.md，说明默认目录、覆盖方式、迁移提示与不自动删除本地密钥文件。
- [x] 同步 `anp-identity` 与 `anp-platform-adapter` main specs。
- [x] 归档到 `openspec/changes/archive/2026-07-07-protect-anp-runtime-secrets/`。

## `return-authentication-info` 完成内容

- [x] 新增 `AuthenticationResult`，携带 caller DID 与成功认证响应头。
- [x] 从 verifier `response_headers` 中按大小写不敏感方式白名单提取 `Authentication-Info`。
- [x] 将 `/agent/rpc` 成功 JSON-RPC 响应附带非空 `Authentication-Info`。
- [x] 保持认证失败 challenge 头、错误分类和 JSON-RPC result body 不变。
- [x] 增加认证与 server 单元测试，覆盖成功头、无头和未允许头不透传。
- [x] 更新 README / 插件 README，将 `Authentication-Info` 标记为已支持能力。
- [x] 新增并同步 `anp-authentication-info` main spec。
- [x] 同步 `anp-platform-adapter` 中的 `JSON-RPC 成功响应契约`。
- [x] 归档到 `openspec/changes/archive/2026-07-07-return-authentication-info/`。

## `harden-rpc-bridge` 完成内容

- [x] 收紧 `/agent/rpc` JSON-RPC 请求校验，仅接受单个 JSON-RPC 2.0 对象、非空字符串 `id`、字符串 `method` 与对象 `params`。
- [x] 对 batch、notification、无效 `jsonrpc`、空/数字 `id` 返回 HTTP 400 与 JSON-RPC `-32600`，并明确无效 id 响应 `id` 为 `null`。
- [x] 新增 `ANPBridgeError`，将 bridge 超时、取消、handler 异常、pending 容量耗尽映射为结构化 JSON-RPC `-32603` 错误。
- [x] 引入服务端内部 request id，用于 pending Future、`MessageEvent.message_id` 与 `anp:{request_id}` chat id，客户端 JSON-RPC `id` 仅用于响应回显与 metadata。
- [x] 保持成功 `chat` 响应 `result.response` shape 不变，且 bridge 失败响应不附带成功认证 `Authentication-Info`。
- [x] 增加 bridge、adapter、server 测试，覆盖重复客户端 id 并发隔离、无效请求、超时、取消、handler 异常和 request id 回传。
- [x] 同步 `anp-rpc-bridge` 与 `anp-platform-adapter` main specs。
- [x] 归档到 `openspec/changes/archive/2026-07-07-harden-rpc-bridge/`。

## `support-anp-core-binding` 完成内容

- [x] 新增 ANP Core Binding 最小兼容能力，支持 `anp.core.binding.v1` envelope。
- [x] `chat` 支持从 `params.body.message` 读取文本，并保留 legacy `params.message` 兼容。
- [x] 新增 `anp.get_capabilities` 方法，返回 service DID、supported profiles、supported security profiles、limits 与 supported content types。
- [x] 对 unsupported profile/security profile/invalid params shape 返回 ANP public error code 与 `error.data.anp_code`。
- [x] 更新 OpenRPC 文档，声明 `chat` 与 `anp.get_capabilities` 方法。
- [x] 增加 server 单元测试，覆盖 Core Binding envelope、capabilities、OpenRPC 与错误语义。

## `expand-agent-discovery` 完成内容

- [x] 创建 proposal/design/tasks/spec deltas。
- [x] 将 CollectionPage 设计校准为 ANP-08 JSON-LD 索引形态：`@type: CollectionPage`，`items[0].@id` 指向 `/agent/ad.json`。
- [x] 按 TDD 增加并验证 well-known discovery RED 测试。
- [x] 实现 server 端 `/.well-known/agent-descriptions` 路由、JSON-LD CollectionPage 和 Agent Description 基础字段。
- [x] 更新根 README、插件 README 与本执行状态文件。
- [x] 运行并通过 OpenSpec validate、targeted server tests、ruff/black。
- [x] 通过 `/opsx:verify expand-agent-discovery`。
- [x] 同步 `anp-discovery` main spec 并归档到 `openspec/changes/archive/2026-07-08-expand-agent-discovery/`。

## `harden-test-harness` 完成内容

- [x] 创建 proposal/design/tasks/spec deltas。
- [x] 盘点现有单元、集成与 E2E 测试覆盖，记录到 `openspec/changes/harden-test-harness/test-coverage-audit.md`。
- [x] 收紧 coverage omit，排除测试、helper、缓存与运行态 DID/PEM 文件。
- [x] 按 TDD 增加 Echo E2E fixture 测试，验证旧实现仍读取用户真实 Hermes config。
- [x] 将 Echo E2E 改为使用临时 `HOME` / `HERMES_HOME` 与生成的 mock LLM 最小配置，不再依赖真实 `~/.hermes/config.yaml`。
- [x] 按 TDD 增加 LLM E2E prerequisites 测试，并将 slow flag / provider / API key 检查移动到 gateway 启动前。
- [x] 补齐 JSON-RPC 非字符串 `method`、非对象 `params` invalid request 回归测试。
- [x] 补齐私钥内容损坏备份并重新生成身份的回归测试。
- [x] 更新根 README、插件 README、CLAUDE.md 与本执行状态文件中的测试说明。
- [x] 运行最终 OpenSpec、ruff/black、普通测试、coverage 与 Echo E2E 验证。
- [x] 同步 main specs 并归档到 `openspec/changes/archive/2026-07-08-harden-test-harness/`。

## `package-anp-plugin` 完成内容

- [x] 创建 proposal/design/tasks/spec deltas。
- [x] 校准设计与规格，明确 Hermes 目录插件运行时使用 `.anp_agent.*` 相对导入，开发安装场景支持 `anp_agent.*` 包导入。
- [x] 按 TDD 增加包化边界测试，验证旧实现缺少 `anp_agent` 包、entrypoint 污染 `sys.path` 且 release zip 不含包目录。
- [x] 将运行时代码迁移到 `plugins/anp-agent/anp_agent/` 包。
- [x] 将包内模块导入改为相对导入，根 `__init__.py` 改为轻量 Hermes entrypoint 并移除 `sys.path.insert`。
- [x] 更新 `pyproject.toml`、coverage source、ruff first-party、测试导入与 monkeypatch 路径。
- [x] 更新 release zip 结构，包含 `anp_agent/` 并排除运行态 DID/PEM 与缓存文件。
- [x] 更新根 README、插件 README、CLAUDE.md、`plugin.yaml` 与本执行状态文件中的包化/安装/测试说明。
- [x] 运行最终 OpenSpec、ruff/black、普通测试、coverage 与 Echo E2E 验证。
- [x] 同步 `anp-plugin-packaging`、`anp-platform-adapter` 与 `dialog-plugin-install` main specs。
- [x] 归档到 `openspec/changes/archive/2026-07-08-package-anp-plugin/`。

## `productionize-did-resolver` 完成内容

- [x] 创建 proposal/design/tasks/spec deltas。
- [x] 新增并同步 `anp-did-resolver` main spec，并修改 `anp-auth-error-classification`、`anp-platform-adapter`、`anp-test-harness` 与 `dialog-plugin-install` main specs。
- [x] 按 TDD 增加 resolver policy RED 测试，覆盖 loopback override、非 loopback 拒绝、HTTPS `verify_ssl=True`、timeout 边界、多实例冲突与 DID Document 无效分类。
- [x] 实现 resolver base URL loopback-only 校验、TLS 策略、timeout 上限、wrapper 幂等与冲突 fail fast、resolver 异常安全分类。
- [x] 将集成测试 fixture 改为使用 `ANP_DID_RESOLVER_BASE_URL` loopback override，不再手工 patch SDK resolver。
- [x] 更新根 README、插件 README、CLAUDE.md 与本执行状态文件，明确生产 DID WBA HTTPS 解析与本地 resolver override 边界。
- [x] 运行最终 OpenSpec、ruff/black、普通测试、coverage 与 Echo E2E 验证。
- [x] 归档到 `openspec/changes/archive/2026-07-08-productionize-did-resolver/`。

## `expose-hermes-tools` 完成内容

- [x] 创建 proposal/design/tasks/spec deltas。
- [x] 新增并同步 `anp-hermes-tool-exposure` main spec。
- [x] 新增默认关闭的 `tool_rpc` 配置结构，支持 `enabled`、`allowed_dids`、`allowed_tools`、`allowed_toolsets`、`denied_tools`、`timeout_seconds` 与 `max_result_bytes`。
- [x] 实现 allowlist、denylist、caller DID 授权、schema 参数校验、工具执行、超时/取消/结果过大错误映射与审计记录。
- [x] 将允许暴露的 Hermes registry tool 映射为 `hermes.tool.<tool_name>` JSON-RPC method。
- [x] 更新 `/agent/interface.json`、`/agent/ad.json` 与 `anp.get_capabilities`，仅在 tool RPC 启用且存在 allowlisted 工具时声明 Hermes tools 能力。
- [x] 更新 `/agent/rpc` 方法路由，保持 `chat`、`anp.get_capabilities` 与未知方法行为不变。
- [x] 更新根 README、插件 README、CLAUDE.md 与 OpenSpec 执行状态文档，说明 tool RPC 默认关闭、安全边界与高风险工具不建议暴露。
- [x] 运行并通过 OpenSpec、目标测试、普通测试、coverage、ruff/black 与 Echo E2E 验证。
- [x] 同步 main specs 并归档到 `openspec/changes/archive/2026-07-08-expose-hermes-tools/`。

## 当前收尾审计目标

当前路线图前十个变更均已完成。`review-community-readiness` 负责做最后一轮事实收口：

1. 更新 `docs/anp-hermes-current-implementation-analysis.md` 和 `docs/anp-hermes-openspec-roadmap.md`，移除已经完成的 Top 10 待办口吻，把现状改为“社区参考实现候选”。
2. 复核 README、插件 README、CLAUDE.md 与 main specs，确认 tool RPC 默认关闭、DID resolver 生产边界、包化安装、E2E 测试说明没有互相矛盾。
3. 运行社区就绪验证矩阵：OpenSpec 全量校验、普通测试、coverage、ruff/black、Echo E2E；真实 LLM E2E 作为有凭据时的条件验证。
4. 产出下一阶段 backlog：生产部署指南、ANP SDK 上游 resolver injection、Bearer token 后续请求完整验收、限流/审计持久化、社区示例客户端。

完成 apply 后，下一步应运行 `/opsx:sync review-community-readiness`，再运行 `/opsx:archive review-community-readiness`。

## 验证记录

### `reconcile-anp-spec-docs`

已运行并通过：

```bash
openspec validate reconcile-anp-spec-docs --strict
```

输出：

```text
Change 'reconcile-anp-spec-docs' is valid
```

已运行：

```bash
openspec list
```

归档前输出显示 active changes 仅包含：

```text
reconcile-anp-spec-docs     19/23 tasks
```

归档时 `tasks.md` 已更新为 23/23 tasks 完成。

已运行：

```bash
openspec list --specs
```

输出显示主规格可正常列出：

```text
anp-auth-error-classification
anp-discovery
anp-e2e-echo-test
anp-e2e-llm-test
anp-identity
anp-platform-adapter
anp-rpc-bridge
dialog-plugin-install
```

### `protect-anp-runtime-secrets`

已运行并通过：

```bash
openspec validate protect-anp-runtime-secrets --strict
```

输出：

```text
Change 'protect-anp-runtime-secrets' is valid
```

已运行并通过：

```bash
python3 -m pytest plugins/anp-agent/tests/test_config.py plugins/anp-agent/tests/test_identity.py -v
```

输出摘要：

```text
16 passed
```

已运行并通过：

```bash
cd plugins/anp-agent && ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

归档前已同步 main specs，并由同步子任务运行通过：

```bash
openspec validate protect-anp-runtime-secrets --strict
```

已运行：

```bash
openspec list
```

归档后输出：

```text
No active changes found.
```

### `return-authentication-info`

已运行并通过：

```bash
openspec validate return-authentication-info --strict
```

输出：

```text
Change 'return-authentication-info' is valid
```

已运行并通过：

```bash
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_auth.py /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v
```

输出摘要：

```text
38 passed
```

已运行并通过：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

归档前已同步 main specs，并由同步子任务运行通过：

```bash
openspec validate return-authentication-info --strict
```

已运行：

```bash
openspec list
```

归档后输出：

```text
No active changes found.
```

### `harden-rpc-bridge`

已运行并通过：

```bash
openspec validate harden-rpc-bridge --strict
```

输出：

```text
Change 'harden-rpc-bridge' is valid
```

已运行并通过：

```bash
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_bridge.py /home/peter/anp-hermes/plugins/anp-agent/tests/test_adapter.py /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v
```

输出摘要：

```text
36 passed
```

曾运行一次相对路径测试命令失败，原因是当前工作目录已在 `plugins/anp-agent`，命令仍使用 `plugins/anp-agent/tests/...` 相对路径，pytest 未找到文件且未运行测试；随后已改用绝对路径重跑并通过。

已运行并通过：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

归档前已同步 main specs，并由同步子任务运行通过：

```bash
openspec validate harden-rpc-bridge --strict
```

已运行：

```bash
openspec list
```

归档后输出：

```text
No active changes found.
```

### `support-anp-core-binding`

已运行并通过：

```bash
openspec validate support-anp-core-binding --strict
```

输出：

```text
Change 'support-anp-core-binding' is valid
```

已运行并通过：

```bash
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v
```

输出摘要：

```text
30 passed
```

已运行并通过：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

已运行并通过：

```bash
/opsx:verify support-anp-core-binding
```

输出摘要：

```text
openspec validate support-anp-core-binding --strict: Change 'support-anp-core-binding' is valid
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v: 30 passed
ruff check /home/peter/anp-hermes/plugins/anp-agent && black --check /home/peter/anp-hermes/plugins/anp-agent: All checks passed; 24 files would be left unchanged
```

归档前已同步 main specs，并由同步子任务运行通过：

```bash
openspec validate support-anp-core-binding --strict
```

已运行：

```bash
openspec list --json
```

归档后输出：

```text
No active changes found.
```

### `expand-agent-discovery`

已运行并通过：

```bash
openspec validate expand-agent-discovery --strict
```

输出：

```text
Change 'expand-agent-discovery' is valid
```

已按 TDD 验证 RED 阶段：

```bash
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v
```

输出摘要：

```text
5 failed, 29 passed
```

失败原因符合预期：`/agent/ad.json` 缺少 `protocolType`，且 `/.well-known/agent-descriptions` 返回 404。

已运行并通过：

```bash
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v
```

输出摘要：

```text
34 passed
```

已运行并通过：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

已运行并通过：

```bash
/opsx:verify expand-agent-discovery
```

输出摘要：

```text
openspec validate expand-agent-discovery --strict: Change 'expand-agent-discovery' is valid
python3 -m pytest /home/peter/anp-hermes/plugins/anp-agent/tests/test_server.py -v: 34 passed
ruff check . && black --check .: All checks passed; 24 files would be left unchanged
```

归档前已同步 main specs，并由同步子任务运行通过：

```bash
openspec validate expand-agent-discovery --strict
```

已运行：

```bash
openspec list --json
```

归档后输出：

```text
No active changes found.
```

建议按路线图进入下一个变更：

```text
harden-test-harness
```

### `harden-test-harness`

已运行并通过：

```bash
python3 -m pytest --cov=. --cov-fail-under=85 -q
```

输出摘要：

```text
89 passed, 6 skipped; total coverage 87.21%
```

按 TDD 验证 Echo E2E RED 阶段：

```bash
python3 -m pytest tests/e2e/test_fixtures.py -v --run-e2e
```

输出摘要：

```text
1 failed, 1 passed
```

失败原因符合预期：新增测试证明旧 Echo E2E fixture 仍读取用户真实 `~/.hermes/config.yaml`。

已运行并通过：

```bash
python3 -m pytest tests/e2e/test_fixtures.py -v --run-e2e
```

输出摘要：

```text
4 passed
```

已运行并通过：

```bash
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e
```

输出摘要：

```text
2 passed
```

已运行并通过普通测试：

```bash
python3 -m pytest tests/ -q
```

输出摘要：

```text
92 passed, 9 skipped
```

已运行并通过最终 OpenSpec 校验：

```bash
openspec validate harden-test-harness --strict
```

输出摘要：

```text
Change 'harden-test-harness' is valid
```

已运行并通过格式与 lint 检查：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
24 files would be left unchanged.
```

已运行并通过最终 coverage 检查：

```bash
python3 -m pytest --cov=. --cov-fail-under=85 -q
```

输出摘要：

```text
92 passed, 9 skipped; total coverage 87.90%
```

已运行并通过 Echo E2E：

```bash
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e
```

输出摘要：

```text
2 passed
```

已运行 LLM E2E gating 验证，按预期在缺少 slow flag 或 provider 凭据时于 gateway 启动前 skip：

```bash
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```

输出摘要：

```text
2 skipped
2 skipped
```

已通过 `/opsx:verify harden-test-harness`，已同步 main specs，并归档到：

```text
openspec/changes/archive/2026-07-08-harden-test-harness/
```


### `package-anp-plugin`

已按 TDD 验证包化边界 RED 阶段：

```bash
python3 -m pytest tests/test_packaging.py -v
```

输出摘要：

```text
4 failed
```

失败原因符合预期：当前实现缺少 `anp_agent` 包，根 entrypoint 仍通过 `sys.path.insert` 和顶层 `adapter` 导入工作，现有 zip 不包含 `anp_agent/`。

包化迁移后已运行并通过：

```bash
python3 -m pytest tests/test_packaging.py -v
```

输出摘要：

```text
4 passed
```

已运行并通过 OpenSpec 校验：

```bash
openspec validate package-anp-plugin --strict
```

输出摘要：

```text
Change 'package-anp-plugin' is valid
```

已运行并通过格式与 lint 检查：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
26 files would be left unchanged.
```

已运行并通过普通测试：

```bash
python3 -m pytest tests/ -q
```

输出摘要：

```text
96 passed, 9 skipped
```

已运行并通过 coverage 检查：

```bash
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

输出摘要：

```text
96 passed, 9 skipped; total coverage 88.02%
```

已运行并通过 Echo E2E：

```bash
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e
```

输出摘要：

```text
2 passed
```

已通过 `/opsx:verify package-anp-plugin`，已同步 main specs，并归档到：

```text
openspec/changes/archive/2026-07-08-package-anp-plugin/
```

### `productionize-did-resolver`

已按 TDD 验证 resolver policy RED 阶段：

```bash
python3 -m pytest tests/test_auth.py -v
```

输出摘要：

```text
9 failed, 23 passed
```

失败原因符合预期：旧实现未限制非 loopback resolver override、HTTPS override 固定 `verify_ssl=False`、timeout 边界未收紧、不同 override 会静默覆盖，且 DID Document binding 异常会落入 `-32006`。

实现后已运行并通过目标认证测试：

```bash
python3 -m pytest tests/test_auth.py -v
```

输出摘要：

```text
32 passed
```

已运行并通过目标认证 + 集成测试：

```bash
python3 -m pytest tests/test_auth.py tests/test_integration.py -v
```

输出摘要：

```text
36 passed
```

已运行并通过 OpenSpec 校验：

```bash
openspec validate productionize-did-resolver --strict
```

输出摘要：

```text
Change 'productionize-did-resolver' is valid
```

已运行并通过格式与 lint 检查：

```bash
ruff check . && black --check .
```

输出摘要：

```text
All checks passed!
26 files would be left unchanged.
```

已运行并通过普通测试：

```bash
python3 -m pytest tests/ -q
```

输出摘要：

```text
107 passed, 9 skipped
```

已运行并通过 coverage 检查：

```bash
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

输出摘要：

```text
107 passed, 9 skipped; total coverage 88.90%
```

已运行并通过 Echo E2E：

```bash
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e
```

输出摘要：

```text
2 passed
```

已通过 `/opsx:verify productionize-did-resolver`，已同步 main specs，并归档到：

```text
openspec/changes/archive/2026-07-08-productionize-did-resolver/
```


- `reconcile-anp-spec-docs` 不改业务实现，只校准文档和规格。
- 当前 DID 文档路径按 DID WBA path DID 规则描述：`/agent/e1_<fingerprint>/did.json`。
- `protect-anp-runtime-secrets` 不自动删除当前源码目录中的未跟踪密钥文件；只加 ignore、调整默认目录和提供迁移说明，是否删除本地文件需用户单独确认。
- 当前默认运行态身份目录为 `~/.hermes/data/anp-agent/`；显式 `ANP_DATA_DIR` 和 `gateway.platforms.anp.extra.data_dir` 仍可覆盖。
- `return-authentication-info` 只补齐成功认证 `Authentication-Info` 响应头，不实现 Bearer token 后续请求验收逻辑。
- `support-anp-core-binding` 已实现并归档；`anp.get_capabilities` 不再列为后续 OpenSpec 变更。
- `expand-agent-discovery` 已实现并归档；`/.well-known/agent-descriptions` 不再列为后续 OpenSpec 变更。
- `harden-test-harness` 已实现并归档；coverage、hermetic Echo E2E、LLM E2E 早 skip 与协议关键路径回归测试已完成。
- `package-anp-plugin` 已实现并归档；运行时代码已迁移到 `anp_agent/` 包，根 entrypoint 不再污染 `sys.path`，release zip 已包含包化结构。
- `productionize-did-resolver` 已实现并归档；resolver override 已限制为 loopback 本地测试用途，HTTPS override 保持 TLS 校验，timeout 与多实例冲突边界已加固。
- `expose-hermes-tools` 已实现并归档；Hermes tools 仅在 tool RPC 显式启用、allowlisted 且 caller DID 授权后暴露。
- 当前正在执行收尾审计变更：`review-community-readiness`。完成后应同步 `anp-community-readiness` main spec 并归档。
