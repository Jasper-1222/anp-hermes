## 1. Tool RPC 配置与策略测试

- [x] 1.1 按 TDD 增加配置测试，验证 tool RPC 默认关闭且未配置 allowlist 时不暴露任何工具。
- [x] 1.2 按 TDD 增加配置测试，验证 `tool_rpc.enabled`、`allowed_dids`、`allowed_tools`、`allowed_toolsets`、`denied_tools`、`timeout_seconds` 与 `max_result_bytes` 的加载和默认值。
- [x] 1.3 按 TDD 增加策略测试，验证 denylist 优先于 allowlist，且内置高风险 denylist 默认拒绝 shell、代码执行、文件写入、skill 管理等工具。
- [x] 1.4 按 TDD 增加 caller DID 授权测试，验证未授权 DID 调用工具时返回 JSON-RPC `-32601` 且不泄露工具存在性。

## 2. Tool exposure helper 实现

- [x] 2.1 新增轻量 tool exposure/dispatch helper，封装 Hermes tool discovery、allowlist/denylist、caller DID 授权和 schema 过滤逻辑。
- [x] 2.2 实现 OpenRPC method 名称映射：Hermes registry tool name 映射为 `hermes.tool.<tool_name>`，并保持配置 allowlist 使用原始 tool name。
- [x] 2.3 实现参数 schema 校验，无效参数返回 JSON-RPC `-32602` 且不执行工具 handler。
- [x] 2.4 实现工具调用执行入口，复用 Hermes 高层 tool invocation API 或等效封装，避免直接透传到底层 registry dispatch。
- [x] 2.5 实现工具调用 timeout、最大结果大小、取消和执行失败的安全错误映射。
- [x] 2.6 增加审计日志/元数据记录，默认只记录 caller DID、request id、tool name、状态、错误类别和耗时，不记录完整参数或结果。

## 3. Discovery、OpenRPC 与 capabilities 集成

- [x] 3.1 按 TDD 增加 `/agent/interface.json` 测试，验证 tool RPC 关闭时不声明任何 `hermes.tool.*` 方法。
- [x] 3.2 按 TDD 增加 `/agent/interface.json` 测试，验证 tool RPC 开启且工具 allowlisted 时动态声明对应 `hermes.tool.*` 方法。
- [x] 3.3 更新 OpenRPC 构建逻辑，将 allowlisted Hermes tool schema 转换为 method 参数说明，并跳过不可用或不可转换工具。
- [x] 3.4 更新 `/agent/ad.json` 与 `anp.get_capabilities`，仅在 tool RPC 启用且存在 allowlisted 工具时声明 Hermes tools 能力。
- [x] 3.5 增加 discovery/capabilities 回归测试，覆盖启用、关闭、denylisted 和不可用工具不声明的场景。

## 4. `/agent/rpc` 工具方法路由

- [x] 4.1 按 TDD 增加 `/agent/rpc` 测试，验证 `hermes.tool.*` 在 tool RPC 关闭时返回 JSON-RPC `-32601`。
- [x] 4.2 按 TDD 增加成功工具调用测试，使用 fake/低风险 Hermes tool 验证 allowlisted 工具返回 JSON-RPC 成功响应。
- [x] 4.3 按 TDD 增加错误路径测试，覆盖未授权 DID、denylisted 工具、参数无效、工具执行失败、执行超时和结果过大。
- [x] 4.4 实现 `/agent/rpc` 中 `hermes.tool.*` 方法路由，保持 `chat`、`anp.get_capabilities` 和未知方法现有行为不变。
- [x] 4.5 确保 bridge 失败、认证失败和 tool RPC 失败不会错误附带成功认证 `Authentication-Info` 头。

## 5. 文档与 OpenSpec 同步准备

- [x] 5.1 更新根 README，说明 Hermes tools 暴露能力默认关闭、配置方式、安全边界和不建议暴露的高风险工具类型。
- [x] 5.2 更新插件 README，补充 tool RPC 配置示例、allowlist/denylist、caller DID 授权和测试建议。
- [x] 5.3 更新 CLAUDE.md 与 `docs/anp-hermes-openspec-execution-state.md`，记录当前 active change 与安全约束。
- [x] 5.4 如实现过程中发现 Hermes tool invocation API 与设计不一致，回写 design/spec delta 后再继续实现。

## 6. 最终验证

- [x] 6.1 运行并通过 `openspec validate expose-hermes-tools --strict`。
- [x] 6.2 运行并通过目标测试：`python3 -m pytest tests/test_config.py tests/test_server.py tests/test_bridge.py -v`。
- [x] 6.3 运行并通过普通测试：`python3 -m pytest tests/ -q`。
- [x] 6.4 运行并通过覆盖率检查：`python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q`。
- [x] 6.5 运行并通过格式与 lint：`ruff check . && black --check .`。
- [x] 6.6 运行并通过 Echo E2E：`python3 -m pytest tests/e2e/test_echo.py -v --run-e2e`。
- [x] 6.7 通过 `/opsx:verify expose-hermes-tools` 后，同步 main specs 并归档。
