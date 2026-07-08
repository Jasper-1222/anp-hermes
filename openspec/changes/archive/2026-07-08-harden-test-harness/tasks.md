## 1. 测试配置与基线盘点

- [x] 1.1 盘点现有 `tests/test_server.py`、`tests/test_bridge.py`、`tests/test_auth.py`、`tests/test_identity.py`、`tests/test_integration.py` 与 `tests/e2e/` 覆盖范围，标记哪些 spec scenario 已覆盖、哪些需要补测。
- [x] 1.2 调整 `plugins/anp-agent/pyproject.toml` 中 coverage 配置，使 source/omit 仅统计插件运行时代码并排除测试、helper、缓存和运行态 DID/PEM 文件。
- [x] 1.3 运行覆盖率命令确认配置生效：`python -m pytest --cov=. --cov-fail-under=85 -q`。

## 2. Echo E2E hermetic 化

- [x] 2.1 按 TDD 增加或调整 E2E fixture 测试，证明 Echo E2E 不读取用户真实 `~/.hermes/config.yaml` 且会设置临时 `HOME` / `HERMES_HOME`。
- [x] 2.2 修改 `tests/e2e/conftest.py`，为 mock Echo E2E 生成最小 Hermes config，移除对 `_load_user_hermes_config()` 的依赖。
- [x] 2.3 确保 Echo E2E 子进程环境只注入测试所需变量：`HERMES_HOME`、临时 `HOME`、`ANP_ALLOW_ALL_USERS`、`ANP_DID_RESOLVER_BASE_URL`、mock LLM API key 与 `ANP_HOME_CHANNEL`。
- [x] 2.4 运行 `python -m pytest tests/e2e/test_fixtures.py -v --run-e2e`，确认 fixture 级测试通过。
- [x] 2.5 运行 `python -m pytest tests/e2e/test_echo.py -v --run-e2e`，确认确定性 Echo E2E 通过。

## 3. LLM E2E 早 skip

- [x] 3.1 按 TDD 增加或调整测试，证明未传 `--run-slow-e2e` 时 LLM E2E 在启动 Hermes gateway 前跳过。
- [x] 3.2 修改 LLM E2E fixture，将 `--run-slow-e2e`、provider 与 API key 检查集中到 gateway 启动前；移除测试函数内重复 slow gating。
- [x] 3.3 增加或调整测试，证明缺少 provider/API key 时 skip reason 明确，且不会启动 gateway。
- [x] 3.4 运行 `python -m pytest tests/e2e/test_llm.py -v --run-e2e`，确认默认 E2E 模式下 LLM 测试被跳过且无 gateway 启动副作用。
- [x] 3.5 在有凭据环境中可选运行 `python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e`；若凭据缺失，记录为按预期 skip，不视为失败。

## 4. 协议关键路径回归测试

- [x] 4.1 补齐 JSON-RPC invalid request、unknown method、bridge timeout/cancel/handler exception/pending capacity exhausted 的缺口测试；已有覆盖则只记录并避免重复。
- [x] 4.2 补齐 Core Binding envelope 与 `anp.get_capabilities` 的缺口测试；已有覆盖则只记录并避免重复。
- [x] 4.3 补齐成功认证 `Authentication-Info` 透传、空头不返回和未允许头过滤的缺口测试；已有覆盖则只记录并避免重复。
- [x] 4.4 补齐身份默认目录、显式目录、环境变量优先级、私钥权限、已有身份加载和损坏备份的缺口测试；已有覆盖则只记录并避免重复。
- [x] 4.5 补齐 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json` 与 `anp.get_capabilities` 公开契约的缺口测试；已有覆盖则只记录并避免重复。
- [x] 4.6 运行普通测试套件：`python -m pytest tests/ -q`。

## 5. 文档与执行状态

- [x] 5.1 更新根 `README.md` 的测试说明，区分普通测试、coverage、Echo E2E 与 LLM E2E 前置条件。
- [x] 5.2 更新 `plugins/anp-agent/README.md` 的测试说明，说明 Echo E2E hermetic、LLM E2E 慢速 gating 与 provider 覆盖环境变量。
- [x] 5.3 如需，更新 `CLAUDE.md` 中开发命令，使测试命令与新基线一致。
- [x] 5.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `harden-test-harness` 为当前 active change 与已执行验证。

## 6. 最终验证

- [x] 6.1 运行 `openspec validate harden-test-harness --strict`。
- [x] 6.2 运行 `ruff check . && black --check .`。
- [x] 6.3 运行 `python -m pytest tests/ -q`。
- [x] 6.4 运行 `python -m pytest --cov=. --cov-fail-under=85 -q`。
- [x] 6.5 运行 `python -m pytest tests/e2e/test_echo.py -v --run-e2e`。
- [x] 6.6 通过 `/opsx:verify harden-test-harness` 后，再同步 main specs 并归档。