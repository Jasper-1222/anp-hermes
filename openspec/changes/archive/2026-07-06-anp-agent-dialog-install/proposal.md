## Why

`anp-agent` 插件当前只能通过 `pip install -e .` 或手动符号链接到 `~/.hermes/plugins/` 安装，对普通用户不够友好。参考 IOAT 项目通过对话框发送压缩包地址即可完成插件安装的体验，我们需要为 `anp-agent` 提供同样的能力：用户只需在 Hermes 对话框中发送一个 zip 下载链接，LLM 即可自动完成下载、解压、启用配置和重启 Gateway，并引导用户接入 ANP 测试床。

## What Changes

- 更新 `plugins/anp-agent/README.md` 和 `/home/peter/anp-hermes/CLAUDE.md`：
  - 补充"对话框安装"说明与示例消息。
  - 列出 LLM 应执行的安装步骤（下载、检查、解压、启用、重启）。
  - 说明安装后的测试床接入步骤（`ANP_ALLOW_ALL_USERS`、DID 文档服务器等）。
- 不新增任何 skill、脚本或代码文件，保持零侵入。

## Capabilities

### New Capabilities

- `dialog-plugin-install`: 通过 Hermes 对话框发送 zip 链接安装 `anp-agent` 平台插件（通过文档提示复用 LLM 自主能力）。

### Modified Capabilities

- 无。

## Impact

- 文档更新：`plugins/anp-agent/README.md`、`/home/peter/anp-hermes/CLAUDE.md`。
- 不新增代码文件或 skill。
- 不修改 Hermes 核心代码，零侵入。
- 不改变现有插件接口或行为。
