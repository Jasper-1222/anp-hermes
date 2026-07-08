## Why

当前 `anp-agent` 插件仍以扁平 Python 模块形式放在插件根目录，并在入口中通过 `sys.path.insert(0, plugin_dir)` 让 `from config import ...` 等通用模块名可解析。该做法适合早期 POC，但会增加模块名污染和发布包结构不清晰的风险，不利于作为 ANP 社区参考实现发布与安装。

## What Changes

- 将插件业务代码迁移到唯一 Python 包名下，例如 `anp_agent/`，避免 `config`、`server`、`auth` 等通用顶层模块名污染全局 import 空间。
- 将插件内部导入改为包内相对导入或明确包名导入，移除对插件根目录 `sys.path.insert(0, ...)` 的依赖。
- 调整 `pyproject.toml` 的 setuptools 配置、coverage source、ruff isort first-party 配置与安装元数据，使 editable install、测试和 coverage 针对包化结构运行。
- 保持 Hermes 插件入口 `plugin.yaml` / `__init__.py:register` 可用，确保对话框安装和手动安装仍能加载 `anp` 平台。
- 明确 release zip 结构：zip 解压到 `~/.hermes/plugins/anp-agent/` 后，根目录必须包含 `plugin.yaml`、`__init__.py`、`README.md`、`pyproject.toml` 与 `anp_agent/` 包目录。
- 更新测试导入、E2E 插件链接/安装逻辑与文档中的测试、安装、发布说明。
- 不改变 ANP 协议行为、HTTP 端点、JSON-RPC shape、DID WBA 认证语义或运行态配置优先级。

## Capabilities

### New Capabilities

- `anp-plugin-packaging`: 定义 `anp-agent` 插件的 Python 包化、Hermes 插件入口兼容、release zip 结构与安装后可加载性要求。

### Modified Capabilities

- `anp-platform-adapter`: 要求平台注册入口在包化结构下继续通过 Hermes 插件机制自注册，且不依赖将插件根目录插入全局 `sys.path` 来解析业务模块。
- `dialog-plugin-install`: 要求对话框安装文档和安装校验说明覆盖包化后的 release zip 根目录结构。

## Impact

- 影响插件源码布局：`adapter.py`、`auth.py`、`bridge.py`、`config.py`、`constants.py`、`identity.py`、`server.py` 将迁移到 `plugins/anp-agent/anp_agent/`。
- 影响插件入口：根目录 `__init__.py` 保持为 Hermes entrypoint，但仅作为轻量注册转发层。
- 影响测试：测试导入路径、monkeypatch 路径、coverage source 与 first-party import 配置需要同步更新。
- 影响发布与安装文档：根 README、插件 README、CLAUDE.md 中的安装、测试与 zip 结构说明需要更新。
- 不影响外部 ANP API：`/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json`、`/agent/rpc` 与 DID 文档路径保持不变。
