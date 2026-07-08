## MODIFIED Requirements

### Requirement: 配置来源
适配器 SHALL 同时支持 `config.yaml` 的 `extra` 字段和环境变量，环境变量优先级高于配置文件；当未显式配置 `data_dir` 时，适配器 SHALL 使用与插件源码目录分离的默认运行态数据目录。

#### Scenario: 环境变量覆盖
- **WHEN** 同时设置了 `ANP_HOST` / `ANP_PORT` 环境变量和 `config.yaml` 中的 `host` / `port`
- **THEN** 使用环境变量的值

#### Scenario: data_dir 默认值
- **WHEN** 未设置 `ANP_DATA_DIR` 且 `config.yaml` 中未配置 `data_dir`
- **THEN** `data_dir` 使用 Hermes 用户数据目录下的 `anp-agent` 专用目录

#### Scenario: data_dir 配置文件覆盖
- **WHEN** `config.yaml` 的 `gateway.platforms.anp.extra.data_dir` 配置了路径且未设置 `ANP_DATA_DIR`
- **THEN** `data_dir` 使用配置文件中的路径

#### Scenario: data_dir 环境变量覆盖
- **WHEN** 同时设置了 `ANP_DATA_DIR` 和 `config.yaml` 中的 `data_dir`
- **THEN** `data_dir` 使用 `ANP_DATA_DIR` 的值
