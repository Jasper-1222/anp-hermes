> 本文档是 OpenSpec 变更级别的精简摘要。完整实现细节见任务拆分与代码注释。

## Context

`anp-agent` 插件已完成核心实现并通过 45 项单元/集成测试，但现有测试使用 mock message handler 模拟 Hermes 回调，未验证插件在真实 Hermes gateway 中的加载、生命周期和消息闭环。参考项目 `internet-of-agent-testnet` 的 Hermes E2E 测试依赖外部手动启动 gateway、固定端口和固定数据目录，缺乏隔离性和自动化。本变更引入更高质量、完全自动化、可复现的 E2E 测试。

## Goals / Non-Goals

**Goals:**
- 实现阶段一 E2E 测试：用临时 `HERMES_HOME` 启动真实 Hermes，加载 ANP 插件，通过 echo skill 完成确定性验证。
- 实现阶段二 E2E 测试：接入真实 LLM，验证单轮和多轮对话能力。
- 所有 E2E 测试默认不运行，通过 `--run-e2e` 显式触发。
- 每次测试使用隔离的 `HERMES_HOME`，避免污染用户真实配置和记忆。

**Non-Goals:**
- 不修改 `anp-agent` 插件核心实现。
- 不将 E2E 测试加入默认 CI 流程（避免依赖外部 LLM）。
- 不测试 AP2 支付或 E2EE 加密。

## Decisions

### 决策 1：使用临时 `HERMES_HOME` 隔离测试环境

**选择**：每个 E2E 测试用例使用 `tmp_path` 作为 `HERMES_HOME`，子进程启动 `hermes gateway run` 时继承该环境变量。

**理由**：
- Hermes 的 `get_hermes_home()` 优先读取 `HERMES_HOME` 环境变量。
- 临时目录包含 `config.yaml`、`plugins/`、`skills/`、日志、数据库等全部状态，测试结束后整体删除。
- 参考项目使用固定 `~/.ioat/` 目录，测试间会互相污染；临时目录彻底解决这个问题。

**替代方案**：备份/恢复用户真实 `~/.hermes/` → 风险高，容易破坏用户环境，拒绝。

### 决策 2：阶段一使用 echo skill 而非真实 LLM（强 prompt + 宽松断言）

**选择**：编写一个 `anp-echo` skill，其 SKILL.md 明确指示模型原样返回用户输入，不加解释、不补充内容。阶段一同样会从真实 `~/.hermes/config.yaml` 复制 model/provider 配置，确保 gateway 能正常启动；即使 LLM 被调用，skill 也会将其约束为 echo 行为。

**理由**：
- 真实 LLM 调用慢、成本高、响应不确定。
- Echo skill 让阶段一快速、稳定、无需额外基础设施。
- 不同模型对 prompt 遵循度不一，断言从"精确相等"降级为"响应包含原输入/非空/无 JSON-RPC error"，容忍轻微偏差。

**替代方案**：
- stub model provider → 需要修改 Hermes 内部，侵入性强，拒绝。
- `pre_gateway_dispatch` hook 直接回复 → 测试代码侵入生产插件，破坏零侵入原则，拒绝。

### 决策 3：通过符号链接将 `anp-agent` 注册到临时 `HERMES_HOME/plugins/`

**选择**：测试 fixture 创建 `HERMES_HOME/plugins/anp-agent` → 指向仓库 `plugins/anp-agent/` 的符号链接，并在 `config.yaml` 的 `plugins.enabled` 中启用。

**理由**：
- Hermes 用户插件目录为 `HERMES_HOME/plugins/`。
- 符号链接避免复制，确保测试运行的是当前代码。
- 插件 kind 为 `platform`，非 bundled，需要在 `plugins.enabled` 中显式启用。

**替代方案**：`HERMES_ENABLE_PROJECT_PLUGINS=1` + `./.hermes/plugins/` → 依赖 cwd，不如符号链接稳定。

### 决策 4：自动分配空闲端口

**选择**：测试 fixture 用 `socket.bind(("127.0.0.1", 0))` 申请空闲端口，并写入 config.yaml。

**理由**：
- 参考项目使用固定 `8900/8901`，无法并行运行多个测试。
- 动态端口避免端口冲突，支持 pytest 并行执行（`pytest-xdist`）。

### 决策 5：ANP 调用方身份动态生成

**选择**：每个测试动态生成 caller DID WBA 身份，并用本地 DID 文档服务器绕过 HTTPS 解析。

**理由**：
- 复用现有集成测试中的 `DIDDocumentServer` 和 `build_signed_headers` helper。
- 不依赖外部 DTR 或注册中心。
- 避免测试间身份状态互相干扰。

### 决策 6：阶段一/阶段二均从真实 `~/.hermes/config.yaml` 派生 model 配置

**选择**：测试 fixture 读取当前用户真实 `~/.hermes/config.yaml` 中的 `model` 与 `providers` 配置，写入临时 `HERMES_HOME/config.yaml`。阶段一额外安装 `anp-echo` skill 约束输出；阶段二直接使用该 provider 走正常 agent 流程。

**理由**：
- 复用用户已配好的 LLM provider 和 API key，无需额外环境变量或模板维护。
- 临时 `HERMES_HOME` 仍保证测试隔离，不污染真实配置与记忆。
- 避免阶段一因缺少 provider 导致 gateway 启动失败。

**替代方案**：环境变量注入 → 需要维护额外模板和 secrets，对本地开发不够便利，拒绝。

### 决策 7：E2E 测试默认跳过，通过 `--run-e2e` 触发

**选择**：在 `conftest.py` 中注册 `--run-e2e` 选项，未传入时自动跳过 `e2e/` 目录下的测试。

**理由**：
- E2E 测试需要本地 Hermes 安装，不适合默认运行。
- 与参考项目的 `--run-hermes-e2e` 保持一致风格。
- CI 可单独配置 nightly job，不影响 PR 阶段快速反馈。

### 决策 8：阶段二使用宽松断言

**选择**：真实 LLM 测试不判断具体文字，只验证响应非空、格式正确、无 JSON-RPC error；多轮测试验证返回语义上引用前文。

**理由**：
- LLM 输出非确定性，精确字符串匹配会导致 flaky。
- 语义断言（如"响应包含 Alice"或"响应与用户输入相关"）足够验证端到端链路。

## Risks / Trade-offs

- **[Risk] Echo skill 无法 100% 约束 LLM 行为** → **Mitigation**：使用强 prompt 约束；断言从"精确相等"降级为"包含原输入/非空/无 error"。
- **[Risk] Hermes gateway 启动慢或失败** → **Mitigation**：fixture 设置 30-60 秒启动超时；启动失败时收集 `gateway.log` 便于诊断。
- **[Risk] 真实 LLM 测试成本高、耗时长** → **Mitigation**：阶段二标记为 `slow`，仅在 `--run-e2e --run-slow-e2e` 时运行；默认 CI 跳过。
- **[Risk] 多轮对话中 session 隔离问题** → **Mitigation**：测试时确保 caller DID 相同；实现阶段验证 `chat_id` / `user_id` 分桶行为，必要时调整 adapter 的 session 键生成逻辑。
- **[Risk] 临时 `HERMES_HOME` 路径过长导致某些依赖异常** → **Mitigation**：使用 `tmp_path_factory.mktemp` 的短名目录，避免超过 Unix socket 路径长度限制。

## Migration Plan

1. 阶段一实现完成后，在本地运行 `pytest plugins/anp-agent/tests/e2e/ --run-e2e` 验证通过。
2. 阶段二实现完成后，配置 LLM provider 环境变量，运行 `--run-e2e --run-slow-e2e` 验证。
3. 更新 `README.md` 和 `CLAUDE.md` 中关于 E2E 测试的说明。
4. 不修改 CI 默认流程；nightly E2E job 暂不实现，后续视情况可选添加。

## Open Questions

1. ✅ 本地 Hermes 已安装并可运行 `hermes gateway run`（`v0.18.0`）。
2. ✅ 阶段二 LLM provider：复用真实 `~/.hermes/config.yaml` 中已配置的 provider。
3. ✅ E2E 测试 config.yaml 策略：阶段一用从真实配置派生的 echo 配置；阶段二用从真实配置派生的正常 agent 配置。
