## 1. 版本来源与依赖声明

- [x] 1.1 读取 `/home/peter/agent-network-protocol/anp/pyproject.toml`，确认上游 ANP Python SDK 当前版本为 `0.8.9`。
- [x] 1.2 将 `plugins/anp-agent/pyproject.toml` 中 `project.dependencies` 的 `anp` 依赖更新为 `anp>=0.8.9,<0.9.0`。
- [x] 1.3 将 `plugins/anp-agent/pyproject.toml` 中测试 extras 的 `anp[api]` 依赖更新为 `anp[api]>=0.8.9,<0.9.0`。
- [x] 1.4 将 `clients/anp-client/requirements.txt` 中 `anp` 依赖更新为 `anp>=0.8.9,<0.9.0`。

## 2. 文档与测试约束

- [x] 2.1 更新根 `README.md` 中当前有效的 ANP SDK 依赖说明为 `anp>=0.8.9,<0.9.0`。
- [x] 2.2 更新当前仍作为发布/验证参考的依赖说明文档，避免推荐旧 `0.8.8` 基线；保留已归档 OpenSpec 历史记录不改。
- [x] 2.3 新增或更新轻量测试，断言 plugin 与 skill 的 ANP SDK 依赖边界均为 `>=0.8.9,<0.9.0`。
- [x] 2.4 确认发布打包脚本生成的 skill zip 内 `requirements.txt` 包含 `anp>=0.8.9,<0.9.0`。

## 3. 验证与收口

- [x] 3.1 运行依赖声明相关测试，确认版本边界断言通过。
- [x] 3.2 运行 `anp-client` 测试，确认客户端发现、签名 chat、安全边界和自然语言样例不受影响。
- [x] 3.3 运行发布打包脚本测试，并重新生成 plugin 与 skill zip。
- [x] 3.4 运行插件核心测试或最小导入/包化测试，确认 ANP SDK 版本边界更新未破坏 plugin 导入和核心协议路径。
- [x] 3.5 运行 `openspec validate update-anp-sdk-dependency --type change`，确认 proposal、design、delta specs 和 tasks 一致。
