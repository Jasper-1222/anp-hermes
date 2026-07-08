## Context

`anp-agent` 当前已完成 DID WBA 身份、认证、JSON-RPC bridge、Core Binding、Agent Description 与 well-known discovery 等主链路能力。后续路线图进入插件包化、DID resolver 生产边界和 Hermes tools 暴露前，需要先把测试体系打磨为稳定基线。

当前测试体系的主要缺口集中在四类：

1. coverage 配置使用 `source = ["."]`，容易把测试目录、helper 或运行态产物纳入统计，后续包化前需要先明确覆盖率边界。
2. Echo E2E 当前仍读取用户真实 `~/.hermes/config.yaml`，即使使用 mock LLM，也会因用户本机配置缺失或变化导致确定性测试不够 hermetic。
3. LLM E2E 的慢速 gating 目前在测试函数内执行，fixture 依赖可能先启动或检查 gateway 后才跳过，失败成本偏高。
4. 已完成的 P0/P1 协议路径已有单元测试，但需要以测试基线的形式固定关键回归覆盖范围，避免后续重构弱化 JSON-RPC 错误语义、`Authentication-Info`、身份持久化和发现/能力文档契约。

本变更只加固测试与文档，不改变生产端点和运行时协议行为。

## Goals / Non-Goals

**Goals:**

- 明确 coverage source/omit，使覆盖率仅衡量插件运行时代码，不统计测试、E2E helper、缓存或运行态文件。
- 让 Echo E2E 完全使用临时 `HOME` / `HERMES_HOME` / Hermes config 与 mock LLM，默认不读取、不依赖、不修改用户真实 `~/.hermes/config.yaml`。
- 让 LLM E2E 在未传 `--run-slow-e2e` 或缺少 provider/API key 时尽早跳过，跳过前不启动 Hermes gateway。
- 补齐关键协议路径的回归测试清单，并将这些测试作为后续重构的基线。
- 更新测试运行文档，使开发者知道普通单元测试、coverage、Echo E2E 和 LLM E2E 的运行条件。

**Non-Goals:**

- 不新增 ANP 业务功能。
- 不改变 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json` 或 `/agent/rpc` 的生产行为。
- 不改变 DID WBA verifier、bridge、Core Binding 或 Agent Description 的协议语义。
- 不做插件包化目录迁移。
- 不引入 CI secret 管理或远程服务依赖。
- 不要求真实 LLM E2E 在无凭据环境中运行。

## Decisions

### Decision 1: coverage 以插件运行时代码为 source，测试目录显式 omit

采用 `plugins/anp-agent` 当前平铺模块布局下最小可行的 coverage 配置：source 指向运行时代码文件所在目录，omit 排除 `tests/*`、`tests/e2e/*`、`tests/helpers/*`、`__pycache__/*` 和可能的运行态 DID/PEM 文件。

原因：当前插件尚未包化为唯一 Python package，不能提前切到 `--cov=anp_agent`。在现有布局下先把统计边界收紧，后续 `package-anp-plugin` 再同步调整 coverage source。

替代方案：立即包化后再修 coverage。该方案范围过大，会把测试体系加固和插件发布结构重构耦合，违背本变更“不做插件包化”的边界。

### Decision 2: Echo E2E 不再读取真实 Hermes config

Echo E2E 使用 fixture 直接写入最小 Hermes config：

- 临时 `HERMES_HOME` 和临时 `HOME`。
- `gateway.platforms.anp` 指向测试端口与临时 `data_dir`。
- `plugins.enabled` 仅启用 `anp-agent`。
- `model/providers` 指向本地 mock LLM。
- `ANP_ALLOW_ALL_USERS=1`、`ANP_DID_RESOLVER_BASE_URL`、`ANP_E2E_API_KEY` 仅注入子进程环境。

原因：阶段一 Echo E2E 的价值是确定性验证 Hermes gateway + 插件 + mock LLM 的链路，不应因用户真实 provider 配置缺失而跳过或失败。

替代方案：继续复制真实配置后覆盖 provider。该方案保留了隐藏依赖，且可能把用户配置中的其他 gateway/skills/plugins 设置带入测试。

### Decision 3: LLM E2E 在 fixture 层早跳过

将 `--run-slow-e2e`、provider 和 API key 检查集中到 LLM gateway fixture 启动前；测试函数不再承担慢速 gating。若未满足条件，跳过发生在启动 Hermes 子进程之前。

原因：真实 LLM E2E 是可选慢速测试，skip 应尽早、低成本、无副作用。

替代方案：保留测试函数内 `_skip_without_slow_e2e()`。该方案可能在 fixture resolution 之后才执行，不能保证跳过前无子进程或临时状态创建。

### Decision 4: 协议路径测试以“关键回归清单”补齐，不重写已有测试

优先复用已有测试文件：

- `tests/test_server.py`：JSON-RPC request validation、Core Binding envelope、capabilities、发现端点、响应头行为。
- `tests/test_bridge.py`：超时、取消、handler 异常、pending 容量与 request id 隔离。
- `tests/test_auth.py`：认证结果、header filtering、错误分类。
- `tests/test_identity.py`：默认目录、显式目录、私钥权限、损坏备份。
- `tests/test_integration.py`：真实签名链路和公开端点。

本变更只补缺口，不为了“集中测试”而迁移或改名现有测试。

原因：保持 surgical changes，避免测试重排带来的无关 diff。

替代方案：新建一个大而全的 `test_protocol_regression.py`。该方案容易重复现有覆盖并降低定位清晰度。

### Decision 5: 文档只说明运行方式和边界，不承诺 CI secret 行为

README/插件 README/CLAUDE 中只更新：

- 普通测试和 coverage 命令。
- Echo E2E 不依赖真实 LLM/API key。
- LLM E2E 需要 `--run-e2e --run-slow-e2e` 和 provider/API key。
- 可用环境变量临时覆盖 LLM provider。

不新增 GitHub Actions secret、发布流水线或真实 LLM 自动化策略。

原因：当前变更目标是本地测试基线，不扩大到 CI 运维。

## Risks / Trade-offs

- [Risk] Echo E2E 最小 config 与用户真实 Hermes 配置差异较大，可能漏掉真实配置组合问题。→ Mitigation：真实 LLM E2E 仍保留读取/覆盖真实 provider 的路径，Echo E2E 只承担确定性链路验证。
- [Risk] coverage omit 过宽可能隐藏测试 helper 中的缺陷。→ Mitigation：helper 可由单独测试验证；coverage 门槛只用于运行时代码质量，不用于 helper 质量度量。
- [Risk] 早 skip LLM E2E 可能让开发者误以为真实 LLM 已验证。→ Mitigation：skip reason 必须明确缺少的 flag 或环境变量；文档明确 Echo E2E 与 LLM E2E 的区别。
- [Risk] 补协议回归测试可能与已有测试重复。→ Mitigation：先盘点现有测试，只为缺失 scenario 新增断言；不重写已覆盖路径。
- [Risk] 临时 `HOME` 可能影响 hermes 子进程查找插件或配置。→ Mitigation：同时显式设置 `HERMES_HOME`，并在 fixture 内写入完整 config、插件 symlink 与必要环境变量。

## Migration Plan

1. 先更新测试配置和 E2E fixture，保持现有单元测试通过。
2. 为 Echo E2E 编写/调整 fixture 测试，验证不会读取真实 `~/.hermes/config.yaml`，再实现最小 config 写入。
3. 为 LLM E2E 编写/调整早 skip 测试，再移动 slow gating 到 fixture 层。
4. 补齐协议关键路径测试缺口，每个新增行为先跑 RED，再实现或调整测试 helper。
5. 更新文档与执行状态。
6. 验证：OpenSpec strict、普通测试、coverage、Echo E2E、ruff/black；真实 LLM E2E 作为有凭据环境的可选慢速验证。

Rollback 策略：本变更不迁移数据、不改生产协议；如 E2E fixture 在特定环境不稳定，可回滚测试 fixture 和文档，不影响插件 runtime。