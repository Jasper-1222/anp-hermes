## MODIFIED Requirements

### Requirement: 通用 skill 安装包边界
`anp-client` skill SHALL 定义平台无关的安装包边界，使同一 skill 内容可通过压缩包、skill 发布网站、URL 下载或 ClawHub 等来源分发。安装包根目录 SHALL 至少包含 `SKILL.md`、`README.md`、`requirements.txt` 和 `scripts/`，且 MUST NOT 包含运行态 DID、私钥、临时文件、软链接或仓库绝对路径依赖。`requirements.txt` 中的 ANP Python SDK 依赖 SHALL 声明为 `anp>=0.8.9,<0.9.0`。

#### Scenario: 安装包内容清单
- **WHEN** 用户阅读 README 或发布检查清单
- **THEN** 文档说明安装包根目录包含 `SKILL.md`、`README.md`、`requirements.txt` 和 `scripts/`
- **AND** 文档说明 `tests/` 可留在源码仓库内，不要求进入最终用户安装包

#### Scenario: 安装包安全检查
- **WHEN** 执行发布前检查
- **THEN** 检查确认安装包内容不包含 `did.json`、`private_key.pem`、临时文件、备份文件或软链接
- **AND** 检查确认安装包脚本不包含当前仓库根目录或其他本机绝对路径依赖

#### Scenario: skill 依赖边界与最新上游基线一致
- **WHEN** 开发者检查 `clients/anp-client/requirements.txt`
- **THEN** 文件声明 ANP SDK 依赖为 `anp>=0.8.9,<0.9.0`
- **AND** 发布脚本生成的 skill zip 内 `requirements.txt` 包含相同依赖边界
