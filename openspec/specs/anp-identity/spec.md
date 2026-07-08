# anp-identity Specification

## Purpose

定义 `anp-agent` 插件的 DID WBA 身份生命周期：首次启动自动生成 `did:wba:` 身份，将 DID 文档与私钥 PEM 持久化到配置的数据目录，并在后续启动时加载已有身份。

## Requirements

### Requirement: DID WBA 身份自动生成
插件 SHALL 在首次启动时自动生成一个符合 ANP 规范的 DID WBA 身份（`did:wba:`），无需用户手动创建或提供私钥。

#### Scenario: 首次启动
- **WHEN** 插件未检测到已持久化的 DID 文档时
- **THEN** 调用 `anp.authentication.create_did_wba_document` 生成 DID 文档、公钥和私钥

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

### Requirement: 身份加载
插件 SHALL 在后续启动时从本地加载已有身份，而不是重复生成。

#### Scenario: 已有身份存在
- **WHEN** 启动时检测到有效的 DID 文档和对应私钥
- **THEN** 插件直接加载并使用该身份，不生成新身份

### Requirement: DID 身份持久化测试覆盖
插件测试体系 SHALL 对 DID WBA 身份持久化边界提供回归测试，确保运行态身份不会回退到源码目录或不安全权限。

#### Scenario: 默认目录测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖未显式配置 `data_dir` 时 DID 文档和私钥写入 Hermes 用户数据目录下的 `anp-agent` 专用目录，而不是插件源码目录

#### Scenario: 显式目录与环境变量测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖配置文件 `data_dir` 和 `ANP_DATA_DIR` 均可覆盖默认身份目录，且环境变量优先级最高

#### Scenario: 私钥权限和损坏备份测试覆盖
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖私钥 PEM 文件权限为 `0o600`，并覆盖损坏 DID 文档或私钥会被备份后重新生成身份
