# anp-plugin-packaging Specification

## Purpose

定义 `anp-agent` 插件的 Python 包化、Hermes 插件入口兼容、release zip 结构与安装后可加载性要求，确保插件可作为独立发布包安装，同时避免通用顶层模块名污染 Hermes 运行时。

## Requirements

### Requirement: 插件业务代码使用唯一 Python 包名
`anp-agent` 插件 SHALL 将业务运行时代码放入唯一 Python 包 `anp_agent`，不得依赖 `adapter`、`config`、`server`、`auth` 等通用顶层模块名作为插件内部导入路径。

#### Scenario: 包内模块可导入
- **WHEN** 在已安装或源码开发环境中导入 `anp_agent.adapter`、`anp_agent.config`、`anp_agent.server` 与 `anp_agent.auth`
- **THEN** 这些模块可成功导入，并使用包内相对导入解析自身依赖

#### Scenario: 根目录不暴露业务模块导入契约
- **WHEN** 插件完成包化后
- **THEN** 业务代码导入路径以 `anp_agent.*` 为准，不要求调用方通过顶层 `adapter`、`config`、`server` 或 `auth` 导入业务模块

### Requirement: 插件入口不污染全局 import 路径
Hermes 插件根目录的 `__init__.py` SHALL 保持 `register(ctx)` entrypoint，但不得通过将插件根目录插入 `sys.path` 来解析业务模块。

#### Scenario: 注册入口不调用 sys.path.insert
- **WHEN** Hermes 或测试加载插件根目录 `__init__.py`
- **THEN** entrypoint 不调用 `sys.path.insert(0, plugin_dir)` 或等效逻辑将插件根目录加入全局模块搜索路径

#### Scenario: 注册入口仍可注册平台
- **WHEN** Hermes 按目录插件加载方式将根目录 `__init__.py` 作为 package 加载并调用 `register(ctx)`
- **THEN** 插件通过 `ctx.register_platform()` 注册名为 `anp` 的 Hermes 平台，且 entrypoint 通过相对导入 `.anp_agent.adapter.ANPAdapter` 创建 adapter factory

### Requirement: Python 打包配置匹配包化结构
插件 SHALL 在 `pyproject.toml` 中声明可安装的 `anp_agent` 包，并让 editable install、测试、lint、format 与 coverage 命令针对包化结构运行。

#### Scenario: editable install 后包可导入
- **WHEN** 开发者在 `plugins/anp-agent` 下运行 `python3 -m pip install -e ".[test,dev]"`
- **THEN** Python 环境可导入 `anp_agent` 包及其运行时模块

#### Scenario: coverage 使用包名口径
- **WHEN** 开发者运行 coverage 测试
- **THEN** coverage source 或命令以 `anp_agent` 为运行时代码统计边界，并继续满足覆盖率阈值

### Requirement: release zip 结构可被 Hermes 插件安装目录直接加载
发布用 `anp-agent.zip` SHALL 包含 Hermes 插件根目录所需文件和 `anp_agent` 包目录，且不得包含运行态 DID/PEM、缓存目录或测试生成文件。

#### Scenario: zip 解压后根目录结构正确
- **WHEN** `anp-agent.zip` 被解压到 `~/.hermes/plugins/anp-agent/`
- **THEN** 该目录根下包含 `plugin.yaml`、`__init__.py`、`README.md`、`pyproject.toml` 与 `anp_agent/`

#### Scenario: zip 不包含运行态敏感文件
- **WHEN** 检查发布 zip 内容
- **THEN** zip 中不包含 `did.json`、`*.pem`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`.coverage` 或 `*.bak.*`

### Requirement: 包化迁移测试覆盖
插件测试体系 SHALL 覆盖包化导入、entrypoint 注册、zip 结构与既有协议行为，确保包化不改变对外 ANP 行为。

#### Scenario: 普通测试覆盖包化迁移
- **WHEN** 运行普通测试套件
- **THEN** 测试覆盖 `anp_agent` 包导入、模拟 Hermes loader 的根 entrypoint 注册、无全局 `sys.path` 污染和 release zip 内容检查

#### Scenario: 协议回归保持不变
- **WHEN** 运行普通测试、coverage 和 Echo E2E
- **THEN** 既有 ANP discovery、identity、authentication、Core Binding、JSON-RPC bridge 与 E2E echo 行为保持通过
