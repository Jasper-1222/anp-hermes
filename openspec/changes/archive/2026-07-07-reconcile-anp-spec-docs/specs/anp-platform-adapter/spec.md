## ADDED Requirements

### Requirement: OpenSpec 状态说明
项目开发文档 SHALL 将已归档变更和当前活跃变更区分说明，不得将已归档的 `create-anp-hermes-plugin` 描述为当前进行中的变更。

#### Scenario: 查看项目开发指南
- **WHEN** 开发者阅读 `CLAUDE.md` 中的 OpenSpec 说明
- **THEN** 文档指向当前活跃变更或通用 OpenSpec 命令，而不是已归档的历史变更
