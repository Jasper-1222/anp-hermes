## 1. 包化边界测试

- [x] 1.1 增加包导入测试，先验证当前实现缺少 `anp_agent` 包时测试失败。
- [x] 1.2 增加根 entrypoint 注册测试，通过 importlib 模拟 Hermes loader 将插件根目录 `__init__.py` 作为 package 加载，覆盖 `register(ctx)` 仍注册 `anp` 平台且 adapter factory 指向包内 `ANPAdapter`。
- [x] 1.3 增加 entrypoint 不污染 `sys.path` 的测试，先验证当前 `sys.path.insert(0, plugin_dir)` 行为会失败。
- [x] 1.4 增加 release zip 内容检查测试，覆盖根目录必须包含 `plugin.yaml`、`__init__.py`、`README.md`、`pyproject.toml` 与 `anp_agent/`，且不得包含 DID/PEM、缓存、coverage 或备份文件。

## 2. 业务模块包化迁移

- [x] 2.1 创建 `plugins/anp-agent/anp_agent/` 包目录与包内 `__init__.py`。
- [x] 2.2 将 `adapter.py`、`auth.py`、`bridge.py`、`config.py`、`constants.py`、`identity.py`、`server.py` 移入 `anp_agent/`。
- [x] 2.3 将包内模块导入改为相对导入或明确包名导入，避免依赖顶层 `adapter`、`config`、`server`、`auth` 等模块名。
- [x] 2.4 将根目录 `__init__.py` 改为轻量 Hermes entrypoint，通过相对导入 `.anp_agent.adapter.ANPAdapter` 注册平台，并移除 `sys.path.insert`。
- [x] 2.5 删除或避免保留旧顶层业务模块兼容 shim，确保业务导入路径只有 `anp_agent.*`。

## 3. 打包配置与测试适配

- [x] 3.1 更新 `pyproject.toml` 的 setuptools 配置，使 editable install 包含 `anp_agent` 包。
- [x] 3.2 将 coverage source / 命令口径调整为 `anp_agent`，并保留测试、helper、缓存、DID/PEM 与备份文件排除。
- [x] 3.3 更新 ruff isort first-party 配置为 `anp_agent`。
- [x] 3.4 更新所有单元测试、集成测试和 E2E fixture 的导入与 monkeypatch 路径。
- [x] 3.5 运行并修复包化边界测试，确认第 1 组 RED 测试转为 GREEN。

## 4. 发布结构与文档

- [x] 4.1 更新根 README、插件 README 与 CLAUDE.md，说明包化后的目录结构、测试命令和 release zip 根目录要求，并修正 `plugin.yaml` 中 `ANP_DATA_DIR` 的过期默认目录说明。
- [x] 4.2 更新对话框安装说明，要求安装检查 `plugin.yaml`、`__init__.py` 与 `anp_agent/` 位于插件根目录。
- [x] 4.3 更新 `docs/anp-hermes-openspec-execution-state.md`，记录 `package-anp-plugin` 当前 active change 与执行进度。
- [x] 4.4 检查现有 `plugins/anp-agent/anp-agent.zip` 或发布 zip 生成方式，确保不会包含运行态 DID/PEM、缓存、coverage 或备份文件。

## 5. 验证与收尾

- [x] 5.1 运行 `openspec validate package-anp-plugin --strict`。
- [x] 5.2 在 `plugins/anp-agent` 下运行 `ruff check . && black --check .`。
- [x] 5.3 在 `plugins/anp-agent` 下运行 `python3 -m pytest tests/ -q`。
- [x] 5.4 在 `plugins/anp-agent` 下运行 `python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q`。
- [x] 5.5 在 `plugins/anp-agent` 下运行 `python3 -m pytest tests/e2e/test_echo.py -v --run-e2e`。
- [x] 5.6 通过 `/opsx:verify package-anp-plugin` 后，同步 main specs 并归档。
