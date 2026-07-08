## 1. Resolver policy 测试（RED）

- [x] 1.1 新增 loopback `ANP_DID_RESOLVER_BASE_URL` 成功认证测试，使用真实签名请求且不手工 patch SDK resolver。
- [x] 1.2 新增非 loopback resolver override 初始化失败测试。
- [x] 1.3 新增 HTTPS override 调用 SDK 通用 resolver 时 `verify_ssl=True` 的测试。
- [x] 1.4 新增 timeout 非法、零值、负值与超大值边界测试。
- [x] 1.5 新增多 `ANPAuth` 实例不同 override 配置冲突与相同配置幂等测试。
- [x] 1.6 新增 resolver 返回 DID Document 无效时映射 `-32004` 且不外泄内部细节的测试。

## 2. Resolver policy 实现（GREEN）

- [x] 2.1 在 `auth.py` 中实现 resolver base URL 解析与 loopback-only 校验。
- [x] 2.2 在 `auth.py` 中实现 override 场景的 TLS 参数策略：HTTP loopback 允许无 TLS，HTTPS override 使用 `verify_ssl=True`。
- [x] 2.3 收紧 `ANP_DID_RESOLVE_TIMEOUT` 解析，非法/零/负数回退默认值，超大值限制到上限。
- [x] 2.4 实现 resolver wrapper 配置幂等与不同非空 override 冲突 fail fast。
- [x] 2.5 补齐 resolver wrapper 异常包装，将网络/timeout 映射 `-32002`，DID document invalid/proof/binding 映射 `-32004`。
- [x] 2.6 运行目标认证测试，确认 RED 测试转 GREEN 且既有认证行为不回归。

## 3. 集成与 E2E 回归

- [x] 3.1 更新集成测试 fixture，优先使用 `ANP_DID_RESOLVER_BASE_URL` loopback override，而不是手工 patch SDK resolver。
- [x] 3.2 运行 `tests/test_auth.py` 与 `tests/test_integration.py`，确认 resolver policy 与真实 JSON-RPC 调用均通过。
- [x] 3.3 运行 Echo E2E，确认测试环境仍可通过临时 loopback resolver override 完成端到端链路。

## 4. 文档与 OpenSpec 状态

- [x] 4.1 更新根 README，说明生产 DID WBA HTTPS 解析与本地 resolver override 边界。
- [x] 4.2 更新插件 README，补充 `ANP_DID_RESOLVE_TIMEOUT`、`ANP_DID_RESOLVER_BASE_URL` 的用途、限制与生产部署说明。
- [x] 4.3 更新 CLAUDE.md 中测试床接入说明，明确 resolver override 仅用于本地测试/开发。
- [x] 4.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `productionize-did-resolver` 进入执行、完成内容与验证记录。

## 5. 最终验证、同步与归档

- [x] 5.1 运行 `openspec validate productionize-did-resolver --strict`。
- [x] 5.2 运行 `ruff check . && black --check .`。
- [x] 5.3 运行普通测试 `python3 -m pytest tests/ -q`。
- [x] 5.4 运行 coverage `python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q`。
- [x] 5.5 运行 Echo E2E `python3 -m pytest tests/e2e/test_echo.py -v --run-e2e`。
- [x] 5.6 通过 `/opsx:verify productionize-did-resolver` 后，同步 main specs 并归档。