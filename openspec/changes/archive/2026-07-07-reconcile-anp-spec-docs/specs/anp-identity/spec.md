## MODIFIED Requirements

### Requirement: 私钥本地安全保管
插件 SHALL 将私钥和 DID 文档持久化到本地文件系统，私钥文件权限 SHALL 设置为仅所有者可读写。

#### Scenario: 持久化位置
- **WHEN** 身份生成完成后
- **THEN** DID 文档和私钥 PEM 文件写入配置的数据目录

#### Scenario: 私钥权限
- **WHEN** 私钥 PEM 文件写入磁盘后
- **THEN** 文件权限为 `0o600`，确保只有智能体进程所有者可读取
