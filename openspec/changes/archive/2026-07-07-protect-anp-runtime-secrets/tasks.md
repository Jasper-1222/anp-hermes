## 1. 忽略规则与默认目录

- [x] 1.1 更新 `.gitignore`，忽略 `plugins/anp-agent/did.json`、`plugins/anp-agent/*.pem` 以及可能的临时/备份运行态身份文件。
- [x] 1.2 将 `plugins/anp-agent/constants.py` 中默认 `data_dir` 改为 `~/.hermes/data/anp-agent/`。
- [x] 1.3 确认 `load_config()` 仍保持 `ANP_DATA_DIR` > `extra.data_dir` > 默认值的优先级，并在必要时补充覆盖测试。

## 2. 身份持久化与测试

- [x] 2.1 增加配置测试，验证未配置 `data_dir` 时使用新的默认目录。
- [x] 2.2 增加配置测试，验证 `extra.data_dir` 能覆盖默认目录。
- [x] 2.3 增加配置测试，验证 `ANP_DATA_DIR` 优先于 `extra.data_dir`。
- [x] 2.4 增加或调整身份测试，验证新默认目录/显式目录下生成的私钥权限仍为 `0o600`。
- [x] 2.5 确认身份生成、加载和损坏备份流程不依赖插件源码目录。

## 3. 文档与迁移说明

- [x] 3.1 更新根 `README.md` 的本地启动配置示例，使用新的默认 `data_dir` 或说明通常无需显式配置。
- [x] 3.2 更新 `plugins/anp-agent/README.md` 的配置示例、环境变量说明和注意事项，说明默认目录、覆盖方式与旧身份迁移方式。
- [x] 3.3 更新 `CLAUDE.md` 中的手动安装配置示例，避免推荐把运行态身份材料写入插件安装目录。
- [x] 3.4 在文档中明确当前工作区已有未跟踪密钥文件不会被自动删除；如需清理或迁移，应由用户单独确认。

## 4. 验证与状态更新

- [x] 4.1 运行 `openspec validate protect-anp-runtime-secrets --strict` 并修正规格问题。
- [x] 4.2 运行插件相关单元测试，至少覆盖配置与身份测试文件。
- [x] 4.3 运行 `ruff check .` 与 `black --check .`，或记录未运行原因。
- [x] 4.4 更新 `docs/anp-hermes-openspec-execution-state.md`，记录当前 active change、完成进度和验证结果。
