## Why

当前 DID resolver 通过 monkeypatch ANP SDK 的全局函数实现超时与 base URL override。该方案满足本地测试，但生产环境中存在测试配置误用、TLS 校验边界不清、同进程多实例配置静默覆盖，以及 resolver 异常分类不完整的问题。

本变更将 DID resolver 的生产约束显式化：默认生产路径遵循 DID WBA 标准 HTTPS 解析，`ANP_DID_RESOLVER_BASE_URL` 仅作为本地开发/E2E 测试便利配置，并补齐对应测试与文档。

## What Changes

- 新增 `anp-did-resolver` 能力规格，定义 DID WBA 解析路径、生产默认 resolver、测试/开发 base URL override、TLS 校验边界、timeout 配置与 monkeypatch 兼容边界。
- 限制 `ANP_DID_RESOLVER_BASE_URL`：仅允许 loopback base URL，用于本地开发、测试床和 E2E；非 loopback override 在认证器初始化时 fail fast。
- 将 loopback HTTP override 明确视为本地测试行为；HTTPS override 默认保持 TLS 校验，不再无条件 `verify_ssl=False`。
- 收紧 `ANP_DID_RESOLVE_TIMEOUT`：非法、零值、负值和过大值回退到安全默认/上限，并增加回归测试。
- 避免多个 `ANPAuth` 实例使用不同 resolver 配置时静默覆盖全局 wrapper；相同配置保持幂等。
- 补齐 resolver wrapper 对 DID document 结构、proof、binding 等异常的包装，使其按既有认证错误分类返回安全 JSON-RPC 错误。
- 更新 README、插件 README、CLAUDE.md 与执行状态文档，明确生产 DID 文档发布/解析方式与本地 resolver override 的适用边界。
- 不 fork ANP SDK，不重写 DID WBA method；保留未来迁移到 SDK resolver injection 的设计缝隙。

## Capabilities

### New Capabilities
- `anp-did-resolver`: 定义 `anp-agent` 对调用方 DID WBA 文档解析的生产默认行为、测试 override 策略、TLS/timeout/错误分类与 ANP SDK monkeypatch 兼容边界。

### Modified Capabilities
- `anp-auth-error-classification`: 补充 resolver policy/config、网络、timeout、DID document 无效和内部异常的安全错误分类要求。
- `anp-platform-adapter`: 补充平台运行配置中 resolver 相关环境变量的生产/测试边界说明。
- `anp-test-harness`: 要求测试体系覆盖 resolver override policy、TLS 参数、timeout 边界、多实例冲突与 E2E env 隔离。
- `dialog-plugin-install`: 补充对话安装后的测试床接入说明，明确 `ANP_DID_RESOLVER_BASE_URL` 仅用于本地测试/开发，不是生产部署方案。

## Impact

- 影响代码：`plugins/anp-agent/anp_agent/auth.py` 及相关认证测试。
- 影响测试：`plugins/anp-agent/tests/test_auth.py`、必要时补充 integration/E2E fixture 回归测试。
- 影响文档：根 `README.md`、`plugins/anp-agent/README.md`、`CLAUDE.md`、`docs/anp-hermes-openspec-execution-state.md`。
- 影响运行方式：生产默认继续使用 ANP SDK DID WBA resolver；本地开发/E2E 可继续使用 loopback `ANP_DID_RESOLVER_BASE_URL`。非 loopback override 将被拒绝，避免将测试便利配置误用于生产。