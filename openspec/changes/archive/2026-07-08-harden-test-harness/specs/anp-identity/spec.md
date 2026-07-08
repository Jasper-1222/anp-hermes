## ADDED Requirements

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