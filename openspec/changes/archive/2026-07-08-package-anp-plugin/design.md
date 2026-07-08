## Context

`anp-agent` 当前采用插件根目录扁平模块布局：`adapter.py`、`auth.py`、`bridge.py`、`config.py`、`identity.py`、`server.py` 等业务模块直接位于 `plugins/anp-agent/` 根目录。Hermes 插件入口为 `plugin.yaml` 中的 `__init__.py:register`，根目录 `__init__.py` 通过 `sys.path.insert(0, plugin_dir)` 让这些扁平模块可被 `from adapter import ANPAdapter`、`from config import ...` 等导入解析。

该布局有两个问题：

1. `config`、`server`、`auth` 等模块名过于通用，插入全局 `sys.path` 后可能与 Hermes 进程或其他插件的模块名冲突。
2. release zip 的运行时代码边界不清晰，不利于后续发布、安装校验和社区贡献。

本变更只做包化和发布结构加固，不改变 ANP 协议、HTTP 端点、认证行为或 Hermes 平台注册语义。

## Goals / Non-Goals

**Goals:**

- 将业务模块收敛到唯一包名 `anp_agent` 下。
- 根目录 `__init__.py` 保持为 Hermes 插件 entrypoint，但不再把插件根目录插入全局 `sys.path`。
- 使用包内相对导入或明确包名导入，避免通用顶层模块名污染。
- 更新 `pyproject.toml`，使 editable install、测试、coverage 和发布元数据与包化结构一致。
- 更新测试导入、monkeypatch 路径和 E2E fixture 中的插件文件结构假设。
- 明确 release zip 结构，确保对话框安装后 Hermes 可继续通过 `plugin.yaml` 加载插件。

**Non-Goals:**

- 不改变 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json`、`/agent/rpc` 或 DID 文档路由。
- 不改变 DID WBA 认证、`Authentication-Info`、Core Binding envelope 或 JSON-RPC 错误语义。
- 不引入新运行时依赖。
- 不实现 DID resolver 生产化、Hermes tools 暴露、AP2 支付或 E2EE。
- 不自动删除已有本地运行态文件、缓存文件或用户目录中的安装副本。

## Decisions

### Decision 1: 根 entrypoint 保持在插件根目录，业务代码迁移到 `anp_agent/`

实现形态：

```text
plugins/anp-agent/
├── plugin.yaml
├── __init__.py          # Hermes entrypoint: register(ctx)
├── pyproject.toml
├── README.md
└── anp_agent/
    ├── __init__.py
    ├── adapter.py
    ├── auth.py
    ├── bridge.py
    ├── config.py
    ├── constants.py
    ├── identity.py
    └── server.py
```

根目录 `__init__.py` 只负责通过 Hermes package 上下文中的相对导入 `.anp_agent.adapter` 加载 `ANPAdapter` 并调用 `ctx.register_platform()`。业务模块不再留在根目录。

备选方案：把 `plugin.yaml` entrypoint 直接改为 `anp_agent.plugin:register`。该方案更纯粹，但取决于 Hermes 插件 loader 是否能稳定解析包内模块 entrypoint。为了降低安装兼容风险，本变更保留现有 `__init__.py:register` entrypoint。

### Decision 2: 移除 `sys.path.insert(0, plugin_dir)`，依赖包导入

根 entrypoint 不再修改全局 `sys.path`。Hermes 目录插件加载器会把插件根目录 `__init__.py` 作为 package 加载，因此 entrypoint 使用显式相对导入：

```python
from .anp_agent.adapter import ANPAdapter
```

editable install 或测试环境仍应支持开发者直接导入包：

```python
import anp_agent.adapter
```

包内模块使用相对导入，例如：

```python
from .config import ANPConfig
from .server import ANPServer
```

这样可以避免 `config`、`server`、`auth` 等通用模块名被注入 Python 全局导入搜索路径。

备选方案：保留 `sys.path.insert` 但把插入路径改为包目录。该方案仍会把 `adapter`、`config` 等名字暴露为顶层模块，不能解决污染问题。

### Decision 3: `pyproject.toml` 使用 setuptools package discovery

当前配置 `py-modules = []` 适合扁平源码的早期安装形态。包化后改为发现 `anp_agent` 包，并同步更新：

- coverage source 从 `.` 调整为 `anp_agent`；
- coverage omit 保留 tests/helper/cache/runtime 文件排除；
- ruff isort `known-first-party` 改为 `anp_agent`；
- 测试命令改为 `--cov=anp_agent`。

备选方案：使用 `src/` layout。该方案对普通 Python 包更标准，但 Hermes 插件 zip 需要根目录直接包含 `plugin.yaml` 和 entrypoint。为减少 zip 结构和插件 loader 风险，本变更保持非 `src/` layout。

### Decision 4: 测试先用导入兼容性和 entrypoint 行为锁定迁移边界

实施时先增加或调整测试，覆盖：

- 根 `__init__.py` 不再调用 `sys.path.insert`，并通过模拟 Hermes loader 的 package 加载方式验证相对导入可用；
- `register(ctx)` 仍注册 `anp` 平台；
- 业务模块在开发安装场景下可通过 `anp_agent.*` 导入；
- tests 和 E2E fixture 不再依赖顶层 `adapter` / `config` 等模块名；
- coverage 仍满足 85%。

这类测试可以在移动文件前先失败，证明测试确实覆盖迁移目标。

### Decision 5: release zip 根目录结构保持对话框安装友好

release zip 解压到 `~/.hermes/plugins/anp-agent/` 后，应直接看到：

```text
plugin.yaml
__init__.py
README.md
pyproject.toml
anp_agent/
```

如果 zip 内部带顶层目录，对话框安装文档仍要求将顶层目录内容移入 `~/.hermes/plugins/anp-agent/`，确保 `plugin.yaml` 位于插件根目录。

本变更只定义和验证 zip 结构，不引入完整发布流水线或 GitHub Release 自动化。

## Risks / Trade-offs

- [Risk] Hermes 插件 loader 对包内 import 环境有隐含假设，移除 `sys.path.insert` 后入口导入失败。  
  → Mitigation: 保留根目录 `__init__.py:register` entrypoint，并增加 entrypoint 注册测试；必要时只在入口中做最小、局部的包导入，不恢复全局扁平模块路径。

- [Risk] 大规模移动文件导致测试 monkeypatch 路径遗漏。  
  → Mitigation: 先统一测试导入路径，再移动业务模块；运行普通测试、coverage 和 Echo E2E。

- [Risk] coverage source 改为 `anp_agent` 后覆盖率口径变化。  
  → Mitigation: 同步更新 coverage 配置和命令，继续执行 `--cov-fail-under=85`。

- [Risk] release zip 可能误包含缓存、运行态 DID/PEM 或 egg-info。  
  → Mitigation: 在任务中加入 zip 内容检查，确保只包含插件运行与文档所需文件，并继续依赖 `.gitignore` / coverage omit 防止运行态文件混入。

## Migration Plan

1. 增加或调整测试，锁定包化后的导入路径、entrypoint 注册和 zip 结构要求。
2. 创建 `anp_agent/` 包目录并移动业务模块。
3. 将模块内部导入改为相对导入，根 entrypoint 改为明确导入 `anp_agent.adapter`。
4. 更新 `pyproject.toml`、coverage、ruff isort 和测试导入。
5. 更新 README、插件 README、CLAUDE.md 与 OpenSpec 执行状态说明。
6. 运行验证：OpenSpec strict、ruff/black、普通测试、coverage、Echo E2E。
7. 同步 main specs 并归档。

Rollback 策略：如果包化后 Hermes loader 无法稳定加载，可保留 `anp_agent/` 包，但在根 entrypoint 中加入受限兼容逻辑；只有在测试证明必要时才恢复最小路径调整，且不得恢复通用顶层模块导入作为长期方案。

## Open Questions

- release zip 是否需要在本变更中新增正式构建脚本，还是只定义并测试手工/现有 zip 结构？当前建议：本变更只做结构定义和最小 zip 内容检查，不引入发布自动化。
- 是否同步删除已有根目录旧业务模块，还是保留兼容 shim？当前建议：删除旧业务模块，避免双路径导入造成行为分裂；根目录只保留 Hermes entrypoint。
