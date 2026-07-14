## Context

本项目目前在 plugin 与 client skill 两条安装路径中分别声明 ANP Python SDK 依赖：`plugins/anp-agent/pyproject.toml` 用于 Hermes plugin 开发/安装，`clients/anp-client/requirements.txt` 用于 OpenClaw skill 安装包。本地最新 ANP SDK 源码位于 `/home/peter/agent-network-protocol/anp/pyproject.toml`，其 `[project].version` 为 `0.8.9`；本项目仍以 `anp>=0.8.8,<0.9.0` 作为最低版本。

本变更服务于社区贡献准备：依赖声明应表达“已对最新上游 ANP SDK 基线进行适配”，同时继续通过 `<0.9.0` 避免意外吸收未来破坏性主版本变更。

## Goals / Non-Goals

**Goals:**

- 将 plugin 与 skill 的 ANP SDK 最低版本统一提升到 `0.8.9`。
- 更新当前仍有效的 README、依赖说明和测试断言，使社区阅读材料不再引用旧基线。
- 保持运行时行为不变，并用现有测试确认 `0.8.9` 版本边界下 API 仍兼容。
- 让发布打包脚本继续把更新后的依赖文件纳入 skill zip。

**Non-Goals:**

- 不引入新的 ANP SDK API 或重写认证、resolver、discovery、JSON-RPC bridge 逻辑。
- 不更新已归档 OpenSpec 历史文件中的历史事实；归档内容保留当时的版本记录。
- 不改变 Python 版本下限、Hermes plugin 结构、OpenClaw skill 包结构或安全策略。
- 不依赖联网拉取 PyPI；版本来源以本地 `/home/peter/agent-network-protocol` 源码为准。

## Decisions

1. **统一使用 `anp>=0.8.9,<0.9.0`。**
   - 理由：`0.8.9` 是本地最新上游源码版本，最低版本提升可以避免社区用户安装旧 `0.8.8` 后遇到已修复的上游问题；保留 `<0.9.0` 继续表达主版本兼容边界。
   - 备选：使用 `anp==0.8.9`。放弃原因是这会过度锁死 patch/minor 兼容更新，不利于社区贡献和后续测试床迭代。

2. **只更新当前有效材料，不改归档历史。**
   - 理由：`openspec/changes/archive/`、早期设计和计划文件记录的是历史执行上下文，改写会降低追溯价值。当前发布和贡献入口应更新根 README、plugin pyproject、skill requirements，以及必要的当前验证/研究文档。
   - 备选：全仓库替换所有 `0.8.8`。放弃原因是会污染归档记录，把过去的事实改成现在的版本。

3. **用测试约束依赖声明一致性。**
   - 理由：plugin 与 skill 两处依赖容易再次漂移；新增或扩展轻量测试比依赖人工 grep 更可靠。
   - 备选：仅人工检查。放弃原因是发布脚本和社区贡献准备要求可重复验证。

4. **不改运行时代码。**
   - 理由：用户明确要求基于最新版本更新依赖信息；尚未发现 `0.8.9` 需要 API 迁移。任何运行时调整应由测试失败或独立 OpenSpec 变更驱动。

## Risks / Trade-offs

- **[Risk] 本地环境未安装 `anp 0.8.9`，测试实际仍跑旧版本。** → Mitigation：实现中先更新声明和文档；如需验证真实安装版本，使用本地 `/home/peter/agent-network-protocol/anp` 安装或在后续发布环境中安装依赖后跑测试。
- **[Risk] `0.8.9` 相比 `0.8.8` 有未覆盖行为变化。** → Mitigation：运行 `anp-client` 测试、发布打包测试和插件核心测试；如出现行为差异，按 systematic-debugging 另行定位。
- **[Risk] 历史文档仍可 grep 到 `0.8.8`。** → Mitigation：明确保留归档和历史计划中的旧版本，当前入口文档不再推荐旧基线。
- **[Risk] 提升最低版本会让已有离线环境需要更新依赖。** → Mitigation：这是社区贡献前的有意基线更新；上限不变，升级范围有限。
