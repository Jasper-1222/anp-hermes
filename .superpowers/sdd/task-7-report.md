# Task 7 报告：集成与 E2E 覆盖

## RED

- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_discovery.py::test_discover_cli_json_output -q`
- 结果：RED，退出码 4；目标测试不存在，符合 brief 要求的新增 `discover --json` subprocess 集成覆盖尚未实现。
- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_chat.py::test_chat_cli_json_output -q`
- 结果：RED，退出码 4；目标测试不存在，符合 brief 要求的新增 `chat --json` subprocess 集成覆盖尚未实现。
- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/plugins/anp-agent/tests/e2e/test_anp_client_skill.py -q --run-e2e`
- 结果：RED，退出码 4；目标 E2E 文件尚不存在，且从仓库根运行时 `--run-e2e` 未加载插件 E2E conftest 选项。后续按 brief 从 `plugins/anp-agent` 目录运行 E2E。

## GREEN

- 新增 `discover --json` async subprocess 集成测试，使用本地 aiohttp mock 服务验证 CLI JSON 输出，并确认 discover 不创建个人 DID 身份文件。
- 新增 `chat --json` async subprocess 集成测试，使用本地 aiohttp mock AD/interface/RPC 服务验证 CLI JSON 输出与 DID WBA 签名头。
- 新增真实 Hermes E2E：`plugins/anp-agent/tests/e2e/test_anp_client_skill.py`，复用既有 `hermes_gateway` 与 `anp_caller_identity` fixtures，通过 anp-client CLI 执行 discover 与 chat。
- 生产代码无需修改；现有 CLI 行为已满足 brief 契约。

## 测试结果

- `python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_discovery.py::test_discover_cli_json_output -q` → 1 passed。
- `python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_chat.py::test_chat_cli_json_output -q` → 1 passed。
- `python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_discovery.py /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_chat.py -q` → 48 passed。
- `python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests -q` → 85 passed。
- `cd /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/plugins/anp-agent && python3 -m pytest tests/test_integration.py tests/test_server.py -q` → 50 passed。
- `cd /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/plugins/anp-agent && python3 -m pytest tests/e2e/test_echo.py tests/e2e/test_anp_client_skill.py -v --run-e2e` → 3 passed。
- `cd /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill && python3 -m black --check clients/anp-client/tests/test_discovery.py clients/anp-client/tests/test_chat.py plugins/anp-agent/tests/e2e/test_anp_client_skill.py` → 3 files would be left unchanged。

## Self-review

- 变更仅覆盖 Task 7 指定测试面：client subprocess 集成测试与 plugin E2E 测试。
- 未引入工具 RPC、地址簿、AP2、E2EE、群聊、多轮会话同步或 Core Binding envelope。
- 集成测试使用本地 aiohttp mock 服务与 async subprocess，避免阻塞 pytest event loop。
- E2E 使用既有 mock LLM Hermes gateway fixture，不需要真实 API key。
- 格式检查初次发现 Black drift 后已修复并重跑相关测试。

## Commit hash

- 实现提交：`a579f7545a6b387cdb736bfe734f08cb206d4ae6`

## Concerns

- 无。
