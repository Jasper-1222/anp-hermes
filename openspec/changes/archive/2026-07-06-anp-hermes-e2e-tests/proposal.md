## Why

`anp-agent` 插件已经通过 45 项单元/集成测试验证了身份、认证、桥接和 HTTP 端点的正确性，但这些测试都是在插件级别用 mock 的 message handler 完成的。为了让 ANP 社区信任这个参考实现，需要补充在**真实 Hermes gateway** 环境中运行的端到端测试，验证插件能被 Hermes 加载、消息能进入 Hermes 处理流程、回复能返回给 ANP 调用方。

## What Changes

- 新增 E2E 测试目录 `plugins/anp-agent/tests/e2e/`，默认不随普通测试运行，通过 `--run-e2e` 显式触发。
- 阶段一（确定性 Echo）：
  - 用临时 `HERMES_HOME` 隔离配置、插件、skill 和记忆。
  - 自动启动/停止 `hermes gateway run` 子进程。
  - 为 Hermes 编写 `anp-echo` skill，让模型在测试场景下直接返回用户输入。
  - 使用 ANP SDK 客户端签名调用 `/agent/rpc`，验证 JSON-RPC 响应与请求一致。
- 阶段二（真实 LLM）：
  - 在临时 `HERMES_HOME` 中配置真实 model provider（环境变量注入 API key）。
  - 单轮对话：验证返回非空、格式正确、无 error。
  - 多轮对话：验证 Hermes session 能保留上下文（同一 caller DID 的连续调用）。
- 新增 pytest fixtures：`hermes_home`、`hermes_gateway`、`anp_echo_skill`、`anp_caller_identity`。
- 更新 `pyproject.toml` 添加可选 E2E 依赖（如 `anp[api]` 已在 test extras 中）。
- 更新 `README.md` 说明如何运行 E2E 测试。

## Capabilities

### New Capabilities

- `anp-e2e-echo-test`：在真实 Hermes gateway 中启动 ANP 插件，使用 echo skill 完成确定性端到端验证。
- `anp-e2e-llm-test`：在真实 Hermes gateway 中接入 LLM，完成单轮与多轮对话验证。

### Modified Capabilities

- 无

## Impact

- 新增测试代码，不修改 `anp-agent` 插件核心实现。
- 需要本地已安装 Hermes CLI 和可选的 LLM provider 配置才能运行阶段二。
- CI 中默认不运行 E2E 测试，避免依赖外部 LLM；可配置 nightly job 或手动触发。
- 提升 ANP 社区参考实现的可信度和可复现性。
