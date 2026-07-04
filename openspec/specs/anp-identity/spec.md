# anp-identity Specification

## Purpose
TBD - created by archiving change create-anp-hermes-plugin. Update Purpose after archive.
## Requirements
### Requirement: DID WBA 身份自动生成
插件 SHALL 在首次启动时自动生成一个符合 ANP 规范的 DID WBA 身份（`did:wba:`），无需用户手动创建或提供私钥。

#### Scenario: 首次启动
- **WHEN** 插件未检测到已持久化的 DID 文档时
- **THEN** 调用 `anp.authentication.create_did_wba_document` 生成 DID 文档、公钥和私钥

### Requirement: 私钥本地安全保管
插件 SHALL 将私钥和 DID 文档持久化到本地文件系统，私钥文件权限 SHALL 设置为仅所有者可读写。

#### Scenario: 持久化位置
- **WHEN** 身份生成完成后
- **THEN** DID 文档、私钥 PEM 文件和 `agent.json` 元数据写入配置的数据目录（默认 `~/.hermes/plugins/anp-agent/`）

#### Scenario: 私钥权限
- **WHEN** 私钥 PEM 文件写入磁盘后
- **THEN** 文件权限为 `0o600`，确保只有智能体进程所有者可读取

### Requirement: 身份加载
插件 SHALL 在后续启动时从本地加载已有身份，而不是重复生成。

#### Scenario: 已有身份存在
- **WHEN** 启动时检测到有效的 DID 文档和对应私钥
- **THEN** 插件直接加载并使用该身份，不生成新身份

