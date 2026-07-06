## 1. 基础设施与测试框架

- [x] 1.1 创建 `plugins/anp-agent/tests/e2e/` 目录结构
- [x] 1.2 编写 `conftest.py`，注册 `--run-e2e` 和 `--run-slow-e2e` 选项，未传入时跳过 e2e 测试
- [x] 1.3 实现 `hermes_home` fixture：创建临时 `HERMES_HOME` 目录并在 teardown 时删除
- [x] 1.4 实现 `free_port` helper：通过 `socket.bind(("127.0.0.1", 0))` 申请空闲端口
- [x] 1.5 实现 `wait_for_url` helper：轮询等待端点返回 HTTP 200
- [x] 1.6 实现 `_load_user_hermes_config()` helper：读取真实 `~/.hermes/config.yaml` 的 model/provider 配置

## 2. 阶段一：确定性 Echo E2E

- [x] 2.1 编写 `anp-echo` skill 的 `SKILL.md`，明确指示模型原样返回用户输入、不加解释
- [x] 2.2 实现 `anp_echo_skill` fixture：将 echo skill 写入临时 `HERMES_HOME/skills/anp-echo/`
- [x] 2.3 实现 `hermes_gateway` fixture：链接 `anp-agent` 到临时 plugins 目录、生成 config.yaml（含 echo skill + 从真实配置复制的 provider）、启动/停止 `hermes gateway run`
- [x] 2.4 实现 `anp_caller_identity` fixture：动态生成 caller DID WBA 身份
- [x] 2.5 实现 `did_document_server` fixture：本地托管 caller DID 文档
- [x] 2.6 编写 `test_echo_chat_returns_message`：验证签名调用 `chat` 后返回原消息
- [x] 2.7 编写 `test_echo_ad_json_and_interface_json`：验证未受保护端点可访问
- [x] 2.8 验证阶段一测试在 `--run-e2e` 下通过

## 3. 阶段二：真实 LLM E2E

- [x] 3.1 实现 `llm_hermes_gateway` fixture：在临时 `HERMES_HOME` 中配置从真实配置复制的 model provider，不安装 echo skill
- [x] 3.2 编写 `test_llm_single_turn_chat`：验证单轮对话返回非空、无 error
- [x] 3.3 编写 `test_llm_multi_turn_chat`：验证同一 caller DID 的多轮上下文连续性
- [x] 3.4 将 LLM 测试标记为 `slow`，仅在 `--run-slow-e2e` 时执行
- [x] 3.5 验证阶段二测试在 `--run-e2e --run-slow-e2e` 下通过

## 4. 文档与 CI

- [x] 4.1 更新 `plugins/anp-agent/README.md`，说明如何运行 E2E 测试
- [x] 4.2 更新 `CLAUDE.md`，补充 E2E 测试相关开发命令和约束
- [x] 4.3 在 `.github/workflows/ci.yml` 中保持默认跳过 E2E，nightly job 暂不实现
- [x] 4.4 运行 `ruff check .`、`black --check .` 和完整单元测试，确保无回归

## 5. 验证与归档

- [x] 5.1 运行 `pytest plugins/anp-agent/tests/ -q --cov=. --cov-fail-under=85`，确认覆盖率不下降
- [x] 5.2 运行 `pytest plugins/anp-agent/tests/e2e/ --run-e2e -v`，确认阶段一通过
- [x] 5.3 运行 `/opsx:verify` 检查 OpenSpec 任务状态
- [x] 5.4 归档 `anp-hermes-e2e-tests` OpenSpec 变更
