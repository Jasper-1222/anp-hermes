# Task 6 报告：自然语言样例与文档

## RED

- 新增 `/home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_natural_language_examples.py`。
- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_natural_language_examples.py -q`
- 结果：RED，退出码 2；测试收集阶段因 `anp_client.normalize_natural_language` 不存在而失败，符合新增接口尚未实现的预期。

## GREEN

- 实现 `normalize_natural_language(text: str) -> dict[str, str]` 的确定性归一化逻辑：提取 URL、区分 `endpoint`/`ad_url`、识别 discover/chat 意图、解析引号或 `发送` 后的消息。
- 更新 `/home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/SKILL.md` 中与测试夹具一致的自然语言样例表。
- 更新 `/home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/README.md` 的故障排查、endpoint 限制与 `serve-did` 生产边界说明。
- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests/test_natural_language_examples.py -q`
- 结果：5 passed。
- 运行：`python3 -m pytest /home/peter/anp-hermes/.claude/worktrees/add-anp-client-skill/clients/anp-client/tests -q`
- 结果：83 passed。

## 实现摘要

- 新增自然语言样例契约测试，覆盖 3 个 chat 表达、1 个 discover 表达、1 个缺 URL 错误。
- 只新增固定样例归一化帮助函数；未接入真实 LLM、未新增依赖、未扩大 Phase 1 能力边界。
- 文档明确第一期仅支持 DID WBA + JSON-RPC `chat` 与服务发现，不实现工具 RPC、地址簿、AP2、E2EE、群聊或多轮会话同步。

## 自审

- 变更范围局限于 Task 6 指定文件。
- 自然语言处理为确定性规则，不保存状态、不联网、不调用 LLM。
- 未暴露 `hermes.tool.*` 或任何远端工具调用能力。
- 错误提示复用 `ClientError`，保持 CLI 可展示错误风格。

## Commit hash

- 实现提交：`b6050fc8cbe1efc907e6ffbb0ae72be51971ad32`

## Concerns

- 无。
