## Why

当前 `anp-agent` 已完成最小 ANP/OpenANP 链路和若干协议增强，但测试体系仍有若干会影响社区参考实现可信度的缺口：coverage 统计边界不够明确，E2E 对用户本机 Hermes 配置存在隐式依赖，慢速真实 LLM E2E 的 skip 时机偏晚，且部分关键协议路径缺少可重复的边界测试。

现在需要先加固测试基线，确保后续插件包化、DID resolver 生产边界和 Hermes tools 暴露等变更有稳定、隔离、可验证的回归保护。

## What Changes

- 修正测试覆盖率配置，使 coverage source/omit 与 `plugins/anp-agent` 当前模块布局一致，并避免把测试文件或运行态产物计入覆盖率。
- 加固确定性 Echo E2E，使其使用临时 `HOME` / `HERMES_HOME` 与临时 Hermes config，不依赖或修改用户真实 `~/.hermes/config.yaml`。
- 调整真实 LLM E2E gating，使缺少 `--run-slow-e2e` 或必要 provider 凭据时尽早 skip，避免先启动 gateway 或生成运行态状态后才跳过。
- 增加协议关键路径回归测试，覆盖已实现的 JSON-RPC 错误语义、成功认证响应头、DID 身份持久化边界与公开发现/能力文档契约。
- 更新 README / 插件 README / CLAUDE 或测试说明中与 E2E、coverage、slow test 运行方式相关的文档。
- 不新增业务功能，不改变 ANP HTTP/RPC 对外协议行为。

## Capabilities

### New Capabilities
- `anp-test-harness`: 定义 `anp-agent` 测试体系的隔离性、覆盖率、E2E gating 与协议回归测试要求。

### Modified Capabilities
- `anp-e2e-echo-test`: 将 Echo E2E 从“复制用户真实配置”调整为 hermetic 临时配置，明确不得依赖或修改用户真实 Hermes home。
- `anp-e2e-llm-test`: 明确真实 LLM E2E 必须在慢速标志和凭据检查通过后才启动 gateway，并保持默认跳过。
- `anp-rpc-bridge`: 补充测试覆盖要求，确保 JSON-RPC 错误语义、Core Binding envelope 与并发 request id 隔离有回归保护。
- `anp-authentication-info`: 补充测试覆盖要求，确保成功认证 `Authentication-Info` 只在允许场景透传。
- `anp-identity`: 补充测试覆盖要求，确保默认数据目录、私钥权限、显式目录和损坏备份行为持续受回归保护。

## Impact

- 主要影响测试与测试配置：`plugins/anp-agent/tests/`、`plugins/anp-agent/tests/e2e/`、`plugins/anp-agent/pyproject.toml` 或 pytest/coverage 配置。
- 可能影响文档：根 `README.md`、`plugins/anp-agent/README.md`、`CLAUDE.md` 与 `docs/anp-hermes-openspec-execution-state.md`。
- 不改变生产端点、认证协议、bridge runtime 行为或插件公开 API。
- 不引入新的外部服务依赖，不新增 CI secret 管理机制。