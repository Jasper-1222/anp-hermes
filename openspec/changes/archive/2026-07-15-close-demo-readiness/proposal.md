## Why

ANP Hermes 第一期技术验证链路已经完成，但仓库仍存在社区 README 未集成、CI 不监听默认分支、干净 clone 包测试依赖 ignored zip、缺少 MIT LICENSE、发布资产名不一致，以及状态文档落后于实际进展等收口问题。作为技术 Demo，本变更只修复影响公开体验、可重复验证和事实一致性的 P0/P1，不推进生产化能力。

## What Changes

- 集成面向社区的 ANP × Hermes 技术验证 Demo README。
- 将 GitHub Actions 改为 Python 3.12 单版本门禁，并监听 `master` push/PR。
- 修复当前 Black、Ruff、动态端口和干净 clone 包测试问题。
- 新增 MIT LICENSE，并让 plugin/client zip 都包含许可证。
- 同时生成版本化发布资产与稳定别名。
- 更新 CLAUDE.md、三份状态文档和 main specs 的当前事实。
- 不创建 GitHub Release，不实现生产部署、限流、持久化审计、跨机器 DID、AP2 或 E2EE。

## Capabilities

### New Capabilities

无。本变更只收口现有技术 Demo。

### Modified Capabilities

- `anp-plugin-packaging`: 定义版本化资产、稳定别名、LICENSE 和干净 clone 包测试边界。
- `anp-test-harness`: 定义 Python 3.12 技术 Demo CI 的最低确定性门禁。
- `anp-community-readiness`: 更新已归档进展、文档一致性、验证矩阵和当前非目标。

## Impact

- CI：`.github/workflows/ci.yml`
- 打包与测试：`scripts/package_anp_release.py`、`tests/`、`plugins/anp-agent/tests/`
- 许可证：`LICENSE` 与两个发布包
- 文档：根 README、插件 README、CLAUDE.md、三份进展文档
- OpenSpec：三个 capability delta 与 `anp-client-skill` Purpose
