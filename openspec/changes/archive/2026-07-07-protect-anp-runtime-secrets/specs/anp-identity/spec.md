## MODIFIED Requirements

### Requirement: 私钥本地安全保管
插件 SHALL 将私钥和 DID 文档持久化到本地文件系统；默认数据目录 SHALL 与插件源码目录分离，私钥文件权限 SHALL 设置为仅所有者可读写。

#### Scenario: 默认持久化位置
- **WHEN** 身份生成完成且用户未显式配置 `data_dir`
- **THEN** DID 文档和私钥 PEM 文件写入 Hermes 用户数据目录下的 `anp-agent` 专用目录，而不是插件源码目录

#### Scenario: 显式持久化位置
- **WHEN** 身份生成完成且用户通过配置文件或环境变量显式配置 `data_dir`
- **THEN** DID 文档和私钥 PEM 文件写入用户指定的数据目录

#### Scenario: 私钥权限
- **WHEN** 私钥 PEM 文件写入磁盘后
- **THEN** 文件权限为 `0o600`，确保只有智能体进程所有者可读取
