## Context

当前 `anp-agent` 会将 DID 文档与私钥 PEM 持久化到 `data_dir`。现有默认值位于 `~/.hermes/plugins/anp-agent/`，在手动开发时又常通过 symlink 指向仓库内的 `plugins/anp-agent/`，因此运行态身份材料容易与源码、插件安装目录混放。仓库当前已经出现未跟踪的 `did.json` 与 `*.pem` 文件，说明误写入源码目录的风险已经发生。

同时，身份模块已经通过原子写入保证私钥文件创建时权限为 `0o600`，这部分安全语义需要保留；配置加载也已经支持 `config.yaml extra` 与环境变量覆盖，不能破坏已有部署的显式配置能力。

## Goals / Non-Goals

**Goals:**

- 默认情况下将 DID 文档与私钥 PEM 写入用户 Hermes 数据目录下的插件专用目录，而不是插件源码或插件安装目录。
- 保留 `ANP_DATA_DIR` 与 `gateway.platforms.anp.extra.data_dir` 的显式覆盖能力，并维持环境变量优先级高于配置文件。
- 通过 `.gitignore` 防止当前源码目录中可能生成的运行态身份文件被误提交。
- 更新文档，明确默认目录、覆盖方式、迁移提示和“不自动删除本地密钥”的边界。
- 增加测试覆盖默认目录、显式覆盖和私钥权限 `0o600`。

**Non-Goals:**

- 不实现密钥轮换、加密存储、KMS/HSM 集成或远程密钥托管。
- 不自动移动、删除或覆盖用户当前工作区已有的 `did.json` / `*.pem` 文件。
- 不改变 DID WBA 生成算法、DID path 规则或认证协议行为。
- 不改变 `ANP_DATA_DIR` / `extra.data_dir` 的既有覆盖语义。

## Decisions

### 决策 1：默认 `data_dir` 改为 `~/.hermes/data/anp-agent/`

将默认值从插件目录改为 Hermes 用户目录下的数据子目录：

```text
~/.hermes/data/anp-agent/
```

理由：

- `~/.hermes/plugins/anp-agent/` 是插件安装目录，不适合作为运行态身份材料目录。
- 在本项目开发模式下，该目录可能是指向仓库 `plugins/anp-agent/` 的 symlink，导致私钥写入源码树。
- `~/.hermes/data/anp-agent/` 能表达“用户本机运行态数据”，也与插件代码目录分离。

备选方案：

- 继续使用 `~/.hermes/plugins/anp-agent/`：兼容性最好，但不能解决源码/插件目录混放问题。
- 使用 `~/.config/anp-agent/`：符合部分 Linux 配置习惯，但偏离 Hermes 用户目录，用户不易定位。
- 使用 `~/.local/share/anp-agent/`：更接近 XDG 数据语义，但当前项目文档和 Hermes 约定都围绕 `~/.hermes/`，会增加解释成本。

### 决策 2：覆盖优先级保持不变

`data_dir` 的解析顺序保持为：

1. `ANP_DATA_DIR`
2. `gateway.platforms.anp.extra.data_dir`
3. 默认 `~/.hermes/data/anp-agent/`

理由：已有部署如果显式配置了目录，应继续完全可控；本变更只改变“未显式配置”的默认行为。

### 决策 3：`.gitignore` 只忽略运行态身份产物，不删除现有文件

在仓库忽略规则中加入插件源码目录下可能出现的运行态文件，例如：

```text
plugins/anp-agent/did.json
plugins/anp-agent/*.pem
```

理由：这能防止误提交，同时不破坏用户本地已有身份材料。当前工作区中的未跟踪文件是否删除或迁移，需要用户单独确认。

### 决策 4：测试以配置和身份边界为主

测试重点：

- 未配置 `data_dir` 时，`load_config()` 返回新的默认目录。
- `extra.data_dir` 和 `ANP_DATA_DIR` 仍可覆盖默认值，且环境变量优先。
- `load_or_create_identity()` 在指定目录生成身份后，私钥文件权限仍为 `0o600`。

不新增端到端测试；该变更是本地路径与持久化边界调整，单元测试即可覆盖核心行为。

## Risks / Trade-offs

- [Risk] 已有未显式配置 `data_dir` 的本地环境会在新默认目录生成新的 DID 身份。  
  → Mitigation：文档说明如需复用旧身份，可显式设置 `ANP_DATA_DIR` 或手动迁移旧目录文件。

- [Risk] 用户误以为本变更会清理当前仓库中的未跟踪密钥文件。  
  → Mitigation：proposal、tasks 和文档中明确“不自动删除；删除/迁移需单独确认”。

- [Risk] `~/.hermes/data/anp-agent/` 目录并非 Hermes 强制标准目录。  
  → Mitigation：该目录位于 Hermes 用户目录内且语义清晰；未来若 Hermes 暴露正式数据目录 API，可通过后续变更迁移。

## Migration Plan

1. 更新默认常量与配置测试，使新安装/未配置环境默认写入 `~/.hermes/data/anp-agent/`。
2. 保持显式配置覆盖能力；已有部署可通过 `data_dir` 或 `ANP_DATA_DIR` 继续使用旧目录。
3. 更新文档，提示用户如需复用旧身份，可手动将 `did.json` 与私钥 PEM 迁移到新目录，或显式配置旧目录。
4. 不在实现中自动移动或删除任何已有密钥文件。
5. 若需要回滚，只需将默认常量恢复为旧值；显式配置的部署不受影响。
