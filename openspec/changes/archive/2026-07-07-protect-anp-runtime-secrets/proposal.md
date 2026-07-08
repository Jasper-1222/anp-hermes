## Why

当前 `anp-agent` 的运行态 DID 文档与私钥文件可能默认生成在插件源码目录中，且仓库当前已有未跟踪的 `*.pem` 与 `did.json` 运行态文件，容易在后续开发或打包过程中被误提交。现在需要在继续扩展 ANP 能力前先收紧运行态密钥边界，避免参考实现把本地身份材料与源码混放。

## What Changes

- 将 `plugins/anp-agent/*.pem`、`plugins/anp-agent/did.json` 等运行态身份文件加入 `.gitignore`，防止本地生成的 DID/密钥材料被误提交。
- 调整 `anp-agent` 默认 `data_dir`，使未显式配置时运行态身份材料写入用户 Hermes 数据目录下的插件专用目录，而不是插件源码目录。
- 保留显式 `ANP_DATA_DIR` 与 `gateway.platforms.anp.extra.data_dir` 覆盖能力，确保已有部署可控迁移。
- 更新 README、插件 README 与项目开发说明中的 `data_dir` 示例、迁移提示和安全边界说明。
- 增加配置与身份管理测试，验证默认目录、显式覆盖和私钥文件权限 `0o600`。
- 不自动删除当前工作区已有的未跟踪密钥文件；是否迁移或删除本地文件由用户另行确认。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `anp-identity`：身份持久化要求需要明确默认数据目录不得指向插件源码目录，并继续保证私钥权限为 `0o600`。
- `anp-platform-adapter`：平台配置加载要求需要明确 `data_dir` 的默认值、配置文件覆盖与环境变量覆盖优先级。

## Impact

- 影响插件配置加载与身份持久化路径：`plugins/anp-agent/config.py`、`plugins/anp-agent/identity.py` 及相关测试。
- 影响仓库忽略规则：`.gitignore`。
- 影响文档与示例配置：`README.md`、`plugins/anp-agent/README.md`、`CLAUDE.md`。
- 影响本地开发体验：新身份材料默认写入 Hermes 用户数据目录；已有源码目录中的本地运行态文件不会被自动删除或迁移。
