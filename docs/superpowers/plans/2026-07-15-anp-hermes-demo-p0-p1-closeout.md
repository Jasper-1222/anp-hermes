# ANP Hermes 技术 Demo P0/P1 收口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不实施任何 P2 或生产化能力的前提下，完成 ANP × Hermes 技术 Demo 的 README、CI、最低质量门禁、许可证、发布包命名和事实文档收口。

**Architecture:** 先把现有 README worktree 和设计文档提交到 Git，再通过 `git merge` 集成到统一 `chore/close-demo-readiness` 分支。统一分支使用一个 `close-demo-readiness` OpenSpec change 管理三类变更：确定性验证门禁、双发布包与许可证、文档/规格事实一致性；实现后运行完整本地门禁，同步 main specs 并归档 change。

**Tech Stack:** Python 3.12、pytest、pytest-cov、Ruff、Black、GitHub Actions、OpenSpec 1.5.0、Markdown、ZIP、Hermes 插件机制、ANP Python SDK 0.8.9。

## Global Constraints

- 项目定位是“ANP × Hermes 技术验证 Demo”，不按生产系统扩展质量与运维能力。
- 只完成 P0/P1；不得实现生产部署、Bearer 扩展、限流、并发治理、持久化审计、resolver 上游改造、跨机器 DID 托管、AP2 或 E2EE。
- CI 只使用 Python 3.12；不保留 Python 3.10/3.11/3.12 矩阵。
- 插件覆盖率阈值保持 `>=85%`，不提高阈值。
- 发布脚本必须同时生成版本化资产与稳定别名：`anp-agent-plugin-0.1.0.zip`、`anp-agent.zip`、`anp-client-skill-0.1.0.zip`、`anp-client.zip`。
- 仓库和两个发布包必须包含标准 MIT `LICENSE`。
- 分支集成只允许使用 `git merge` 或 `git cherry-pick`，禁止手工复制覆盖分支文件。
- README worktree 中未提交文件必须先提交；不得在提交前删除该 worktree。
- `.claude/worktrees/` 不加入 Git。
- 官方语言为中文；代码注释、文档、OpenSpec 和提交信息使用中文。
- 不创建 tag、GitHub Release、PR，不执行远端推送。

---

## File Structure

### 分支与规划产物

- Preserve and commit: `.claude/worktrees/docs-anp-hermes-community-readme/README.md` — 已批准的社区 README 草稿。
- Existing committed design: `docs/superpowers/specs/2026-07-15-anp-hermes-demo-p0-p1-closeout-design.md` — 本计划的批准设计。
- Create: `docs/superpowers/plans/2026-07-15-anp-hermes-demo-p0-p1-closeout.md` — 本实施计划。

### OpenSpec change

- Create: `openspec/changes/close-demo-readiness/.openspec.yaml` — spec-driven change 元数据。
- Create: `openspec/changes/close-demo-readiness/proposal.md` — 为什么进行 Demo 收口、改什么、不改什么。
- Create: `openspec/changes/close-demo-readiness/design.md` — CI、打包、许可证和文档同步设计。
- Create: `openspec/changes/close-demo-readiness/tasks.md` — 本轮可验收任务清单。
- Create: `openspec/changes/close-demo-readiness/specs/anp-plugin-packaging/spec.md` — 双名称、LICENSE 和干净 clone 包测试增量。
- Create: `openspec/changes/close-demo-readiness/specs/anp-test-harness/spec.md` — Python 3.12 Demo CI 门禁增量。
- Create: `openspec/changes/close-demo-readiness/specs/anp-community-readiness/spec.md` — 当前状态、文档一致性和验证矩阵增量。

### 代码、测试与 CI

- Create: `LICENSE` — 标准 MIT 许可证正文。
- Modify: `scripts/package_anp_release.py` — 生成四个资产并在两个逻辑发布包中加入根 LICENSE。
- Modify: `tests/test_package_anp_release.py` — TDD 约束四个资产、稳定别名内容和 LICENSE。
- Modify: `tests/test_anp_dependency_versions.py` — 移除 `/home/peter/agent-network-protocol` 的干净 clone 依赖，改验已安装 SDK 版本边界。
- Modify: `plugins/anp-agent/tests/test_packaging.py` — 在临时目录调用打包器，不依赖 ignored `plugins/anp-agent/anp-agent.zip`。
- Modify: `plugins/anp-agent/tests/test_adapter.py` — 连接测试 fixture 使用动态端口 `0`。
- Modify: `plugins/anp-agent/tests/e2e/conftest.py` — Black 格式收口。
- Modify: `scripts/verify_anp_sdk.py` — 清理 Ruff 报告的未使用导入和过期运行路径示例。
- Modify: `.github/workflows/ci.yml` — `master` 单版本完整门禁。

### 文档与 main specs

- Modify: `README.md` — 集成社区 README，更新测试、资产和许可证说明。
- Modify: `plugins/anp-agent/README.md` — 修正尚未发布的 Release 表述、稳定资产名和测试前置条件。
- Modify: `CLAUDE.md` — 技术 Demo 定位、归档状态、仓库结构和完整验证命令。
- Modify: `docs/anp-hermes-openspec-execution-state.md` — active/归档状态和本轮验证记录。
- Modify: `docs/anp-hermes-openspec-roadmap.md` — 已完成扩展与当前 Demo 收口状态。
- Modify: `docs/anp-hermes-current-implementation-analysis.md` — 当前能力、默认审计 sink 和验证基线。
- Modify: `openspec/specs/anp-client-skill/spec.md` — 将占位 Purpose 改为正式中文 Purpose。
- Modified by OpenSpec archive: `openspec/specs/anp-plugin-packaging/spec.md`。
- Modified by OpenSpec archive: `openspec/specs/anp-test-harness/spec.md`。
- Modified by OpenSpec archive: `openspec/specs/anp-community-readiness/spec.md`。

---

### Task 1: 安全保全 README 并建立统一收口分支

**Files:**
- Commit: `.claude/worktrees/docs-anp-hermes-community-readme/README.md`
- Merge: `docs/superpowers/specs/2026-07-14-anp-hermes-community-readme-design.md`
- Merge: `docs/superpowers/plans/2026-07-14-anp-hermes-community-readme.md`
- Merge: `docs/superpowers/specs/2026-07-15-anp-hermes-demo-p0-p1-closeout-design.md`
- Merge: `docs/superpowers/plans/2026-07-15-anp-hermes-demo-p0-p1-closeout.md`

**Interfaces:**
- Consumes: 分支 `worktree-docs-anp-hermes-community-readme` 上未提交的 `README.md`；分支 `docs/close-demo-readiness-design` 上已提交的设计和本计划。
- Produces: 基于 `master` 的统一分支 `chore/close-demo-readiness`，同时包含 README 与所有设计/计划提交。

- [ ] **Step 1: 检查 README worktree 只包含预期差异**

Run:

```bash
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme status --short --branch
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme diff --check
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme diff --stat
```

Expected:

```text
## worktree-docs-anp-hermes-community-readme
 M README.md
README.md | ...
```

`git diff --check` 无输出。若出现 README 之外的修改，停止并报告，不提交未知文件。

- [ ] **Step 2: 在 README worktree 提交 README**

Run:

```bash
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme add README.md
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme commit -m "docs: 更新 ANP Hermes 技术验证项目说明"
```

Expected: 创建只包含 `README.md` 的提交。

- [ ] **Step 3: 将设计/计划分支合入 README 分支**

Run:

```bash
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme merge --no-ff docs/close-demo-readiness-design -m "merge: 合并技术 Demo 收口设计"
```

Expected: 合并成功；README 分支同时包含 README 和四份设计/计划文档，没有手工复制文件。

- [ ] **Step 4: 验证 README worktree 已被 Git 保全**

Run:

```bash
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme status --short --branch
git -C /home/peter/anp-hermes/.claude/worktrees/docs-anp-hermes-community-readme log -3 --oneline --decorate
```

Expected: 工作树无未提交文件；最近历史包含 README 提交和设计合并提交。

- [ ] **Step 5: 从 master 创建统一收口分支**

Run:

```bash
cd /home/peter/anp-hermes
git switch master
git switch -c chore/close-demo-readiness
git merge --no-ff worktree-docs-anp-hermes-community-readme -m "merge: 合并社区 README 与收口设计"
```

Expected: 当前分支为 `chore/close-demo-readiness`，README 与设计/计划均已进入该分支。

- [ ] **Step 6: 验证统一分支范围**

Run:

```bash
git status --short --branch
git log --graph --oneline --decorate -8
git diff --check master...HEAD
```

Expected: 除未跟踪 `.claude/worktrees/` 外无工作区修改；历史显示通过 merge 集成；空白检查通过。

---

### Task 2: 创建单一 OpenSpec Demo 收口变更

**Files:**
- Create: `openspec/changes/close-demo-readiness/.openspec.yaml`
- Create: `openspec/changes/close-demo-readiness/proposal.md`
- Create: `openspec/changes/close-demo-readiness/design.md`
- Create: `openspec/changes/close-demo-readiness/tasks.md`
- Create: `openspec/changes/close-demo-readiness/specs/anp-plugin-packaging/spec.md`
- Create: `openspec/changes/close-demo-readiness/specs/anp-test-harness/spec.md`
- Create: `openspec/changes/close-demo-readiness/specs/anp-community-readiness/spec.md`

**Interfaces:**
- Consumes: 已批准设计 `docs/superpowers/specs/2026-07-15-anp-hermes-demo-p0-p1-closeout-design.md`。
- Produces: 唯一 active change `close-demo-readiness`，为后续代码、CI、打包和文档任务提供验收契约。

- [ ] **Step 1: 创建 spec-driven change 骨架**

Run:

```bash
cd /home/peter/anp-hermes
openspec new change close-demo-readiness \
  --description "收口 ANP Hermes 技术 Demo 的 CI、发布包、许可证与文档事实一致性" \
  --goal "让干净 clone 可验证、master CI 可运行、发布资产与当前文档一致" \
  --json
```

Expected: 输出 JSON 中的 change name 为 `close-demo-readiness`，路径位于 `openspec/changes/close-demo-readiness/`。

- [ ] **Step 2: 写 proposal.md**

Write `openspec/changes/close-demo-readiness/proposal.md`:

```markdown
## Why

ANP Hermes 第一期技术验证链路已经完成，但仓库仍存在社区 README 未集成、CI 不监听默认分支、干净 clone 包测试依赖 ignored zip、缺少 MIT LICENSE、发布资产名不一致，以及状态文档落后于实际进展等收口问题。作为技术 Demo，本变更只修复影响公开体验、可重复验证和事实一致性的 P0/P1，不推进生产化能力。

## What Changes

- 集成面向社区的 ANP × Hermes 技术验证 Demo README。
- 将 GitHub Actions 改为 Python 3.12 单版本门禁，并监听 `master` push/PR。
- 修复当前 Black、Ruff、动态端口和干净 clone 包测试问题。
- 新增 MIT LICENSE，并让 plugin/client zip 都包含许可证。
- 同时生成版本化发布资产与稳定别名。
- 更新 CLAUDE.md、三份状态文档和 main specs 的当前事实。
- 不创建 GitHub Release，不实现生产部署、限流、持久化审计、跨机器 DID、AP2 或 E2EE。

## Capabilities

### New Capabilities

无。本变更只收口现有技术 Demo。

### Modified Capabilities

- `anp-plugin-packaging`: 定义版本化资产、稳定别名、LICENSE 和干净 clone 包测试边界。
- `anp-test-harness`: 定义 Python 3.12 技术 Demo CI 的最低确定性门禁。
- `anp-community-readiness`: 更新已归档进展、文档一致性、验证矩阵和当前非目标。

## Impact

- CI：`.github/workflows/ci.yml`
- 打包与测试：`scripts/package_anp_release.py`、`tests/`、`plugins/anp-agent/tests/`
- 许可证：`LICENSE` 与两个发布包
- 文档：根 README、插件 README、CLAUDE.md、三份进展文档
- OpenSpec：三个 capability delta 与 `anp-client-skill` Purpose
```

- [ ] **Step 3: 写 design.md**

Write `openspec/changes/close-demo-readiness/design.md`:

```markdown
## Context

当前默认分支为 `master`，CI 却监听 `main`；打包脚本只生成版本化文件，而插件 README 使用稳定下载名；插件包测试要求 ignored zip 预先存在；仓库声明 MIT 但没有 LICENSE。项目已有完整本地测试体系，因此只需收敛这些工程与文档边界，不需要生产级扩展。

## Goals / Non-Goals

**Goals:**

- 让 Python 3.12 CI 在 `master` push/PR 上运行 OpenSpec、根级、客户端和插件门禁。
- 让普通测试不依赖固定端口或预生成 ignored zip。
- 让一次打包生成版本化 plugin/client zip 和稳定别名，并包含 MIT LICENSE。
- 让主要文档和 main specs 反映当前技术 Demo 状态。

**Non-Goals:**

- 不创建 tag、Release、PR 或远端推送。
- 不增加生产部署、Bearer 扩展、限流、持久化审计、resolver 上游改造、跨机器 DID、AP2 或 E2EE。
- 不提高覆盖率阈值，不维护多 Python 版本矩阵。

## Decisions

1. CI 固定 Python 3.12，降低技术 Demo 维护成本。
2. 发布脚本返回四个路径；稳定别名是版本化文件的字节级副本。
3. 根 LICENSE 作为 `LICENSE` 归档到 plugin/client zip。
4. 插件包测试直接调用根打包脚本并使用 `tmp_path`，不写仓库 ignored 产物。
5. adapter 测试通过 fixture 显式传入 `port=0`，不停止用户正在运行的 Hermes。
6. OpenSpec 只使用一个 change；P2 只记录为非目标。

## Risks / Trade-offs

- 单版本 CI 不证明 Python 3.10/3.11 兼容；技术 Demo 接受此取舍。
- 本轮不创建 Release，稳定 URL 只是后续发布约定；文档必须用条件式表述。
- 真正的 GitHub Actions 结果要在未来推送后才能观察；本轮以本地命令和 workflow 内容校验为准。
```

- [ ] **Step 4: 写 anp-plugin-packaging delta**

Write `openspec/changes/close-demo-readiness/specs/anp-plugin-packaging/spec.md`:

```markdown
## ADDED Requirements

### Requirement: 技术 Demo 双发布资产与许可证
发布脚本 SHALL 为 plugin 与 client skill 分别生成版本化资产和稳定别名。稳定别名 MUST 与对应版本化资产字节一致，两个逻辑发布包 MUST 在归档根目录包含仓库 MIT `LICENSE`。

#### Scenario: 一次打包生成四个资产
- **WHEN** 开发者以版本 `0.1.0` 运行发布脚本
- **THEN** 输出目录包含 `anp-agent-plugin-0.1.0.zip` 和 `anp-agent.zip`
- **AND** 输出目录包含 `anp-client-skill-0.1.0.zip` 和 `anp-client.zip`
- **AND** 两个稳定别名分别与对应版本化资产字节一致

#### Scenario: 发布包包含许可证
- **WHEN** 开发者检查 plugin 或 client skill zip
- **THEN** 归档根目录包含 `LICENSE`
- **AND** `LICENSE` 内容来自仓库根 MIT 许可证文件

#### Scenario: 干净 clone 可执行包化测试
- **WHEN** 在没有预生成 `*.zip` 的干净 clone 中运行普通测试
- **THEN** 测试在临时目录调用发布脚本生成待检查归档
- **AND** 测试不要求 `plugins/anp-agent/anp-agent.zip` 预先存在
```

- [ ] **Step 5: 写 anp-test-harness delta**

Write `openspec/changes/close-demo-readiness/specs/anp-test-harness/spec.md`:

```markdown
## ADDED Requirements

### Requirement: 技术 Demo 最低 CI 门禁
项目 SHALL 提供 Python 3.12 单版本 GitHub Actions 门禁，并在默认分支 `master` 的 push 与 pull request 上触发。门禁 MUST 覆盖 OpenSpec、根级测试、客户端测试、插件测试、插件覆盖率、Ruff、Black 和发布包构建。

#### Scenario: 默认分支触发 CI
- **WHEN** 提交被 push 到 `master` 或 pull request 以 `master` 为目标分支
- **THEN** CI workflow 被触发
- **AND** workflow 使用 Python 3.12

#### Scenario: CI 覆盖技术 Demo 组件
- **WHEN** CI job 执行
- **THEN** 运行 `openspec validate --all`
- **AND** 运行根级和客户端 pytest
- **AND** 运行根级、客户端和插件 Ruff/Black
- **AND** 构建四个发布资产
- **AND** 运行插件普通测试和 `>=85%` 覆盖率门禁

#### Scenario: 确定性测试不占用固定端口
- **WHEN** 本机已有服务监听默认 ANP 端口
- **THEN** adapter 单元测试仍使用动态端口完成连接与断开验证
- **AND** 测试不要求停止用户服务
```

- [ ] **Step 6: 写 anp-community-readiness delta**

Write `openspec/changes/close-demo-readiness/specs/anp-community-readiness/spec.md`:

```markdown
## MODIFIED Requirements

### Requirement: 社区就绪状态收口
项目 SHALL 准确记录截至 `close-demo-readiness` 之前的 17 个 OpenSpec 变更均已归档。执行 `close-demo-readiness` 期间，该变更 SHALL 是唯一 active change；归档后 active changes SHALL 恢复为空，并记录技术 Demo P0/P1 已完成。

#### Scenario: 执行期间状态准确
- **WHEN** 开发者在本变更执行期间阅读执行状态文档
- **THEN** 文档声明唯一 active change 为 `close-demo-readiness`
- **AND** 文档不再把 `review-community-readiness` 描述为执行中

#### Scenario: 归档后状态准确
- **WHEN** `close-demo-readiness` 已归档
- **THEN** `openspec list --json` 中 active changes 为空
- **AND** 文档记录客户端 skill、双发布包、ANP SDK 0.8.9 和 Demo 收口均已完成

### Requirement: 文档事实一致性审计
项目 SHALL 对根 README、插件 README、CLAUDE.md、执行状态、路线图、实现分析和 main specs 执行事实一致性审计，确保它们对技术 Demo 定位、当前能力、测试命令、发布资产、LICENSE、默认审计 sink 和 OpenSpec 状态的描述一致。

#### Scenario: 主要文档一致
- **WHEN** 开发者阅读主要文档
- **THEN** 文档均说明项目是 ANP × Hermes 技术验证 Demo
- **AND** 文档不声称当前已经创建 GitHub Release
- **AND** 文档不把默认未配置的 audit callback 描述为已持久化审计记录

#### Scenario: 当前能力被准确记录
- **WHEN** 开发者查看仓库结构和能力清单
- **THEN** 文档包含 Hermes plugin、ANP client skill、双发布包和 ANP SDK 0.8.9
- **AND** 不再建议先完成已经归档的 `review-community-readiness`

### Requirement: 社区就绪验证矩阵
项目 SHALL 执行技术 Demo 的最低本地验证矩阵，覆盖 OpenSpec、根级测试、客户端测试、插件普通测试、插件覆盖率、Ruff、Black、本地无凭据 E2E 和发布包构建。

#### Scenario: 必须验证通过
- **WHEN** 执行 Demo 收口
- **THEN** OpenSpec、根级、客户端、插件、覆盖率、Ruff、Black 和发布包构建全部通过
- **AND** 无凭据本地 E2E 通过，真实 LLM E2E 可记录为条件未执行

#### Scenario: 不伪造外部验证
- **WHEN** 本轮未创建 GitHub Release 或未重新运行真实 LLM E2E
- **THEN** 文档不得把这些外部或条件动作描述为本轮已完成

### Requirement: 下一阶段 backlog
项目 SHALL 将生产部署、Bearer 扩展、限流、持久化审计、resolver 上游改造、跨机器 DID、AP2 和 E2EE 明确保留为当前技术 Demo 范围外的可选后续主题，不得在 `close-demo-readiness` 中实施。

#### Scenario: P2 不进入本轮
- **WHEN** 开发者检查本变更的代码、文档和任务
- **THEN** 本变更只包含 Demo P0/P1 收口
- **AND** 不包含任何 P2 或生产级能力实现

#### Scenario: 推荐下一步操作
- **WHEN** `close-demo-readiness` 归档完成
- **THEN** 项目可以保留当前技术 Demo 状态供社区体验
- **AND** 不要求继续创建生产化 OpenSpec change 才能完成本轮
```

- [ ] **Step 7: 写 tasks.md**

Write `openspec/changes/close-demo-readiness/tasks.md`:

```markdown
## 1. 分支与 README 保全

- [ ] 1.1 提交 README worktree 中的 README。
- [ ] 1.2 通过 git merge 集成设计分支和 README 分支。
- [ ] 1.3 从 master 建立统一 `chore/close-demo-readiness` 分支。

## 2. 打包、许可证与干净 clone

- [ ] 2.1 为四个发布资产和 LICENSE 编写失败测试。
- [ ] 2.2 添加根 MIT LICENSE。
- [ ] 2.3 实现版本化资产与稳定别名。
- [ ] 2.4 让插件包化测试在临时目录构建归档。
- [ ] 2.5 移除根级依赖测试对本机上游绝对路径的依赖。

## 3. 最低质量与 CI

- [ ] 3.1 让 adapter 连接测试显式使用动态端口。
- [ ] 3.2 修复已知 Black 和 Ruff 门禁。
- [ ] 3.3 将 CI 改为监听 master 的 Python 3.12 单版本完整门禁。

## 4. 文档与规格事实同步

- [ ] 4.1 更新根 README 与插件 README 的测试、资产和许可证说明。
- [ ] 4.2 更新 CLAUDE.md、执行状态、路线图与实现分析。
- [ ] 4.3 为 `anp-client-skill` 填写正式 Purpose。
- [ ] 4.4 确认文档不宣称本轮已创建 Release 或重新通过真实 LLM E2E。

## 5. 验证与归档

- [ ] 5.1 运行 OpenSpec、根级、客户端、插件、覆盖率、Ruff、Black、E2E 和打包门禁。
- [ ] 5.2 运行干净 clone smoke 验证。
- [ ] 5.3 同步 delta specs 并归档 `close-demo-readiness`。
- [ ] 5.4 确认 active changes 为空并记录最终验证结果。
```

- [ ] **Step 8: 校验 change 并提交**

Run:

```bash
openspec status --change close-demo-readiness --json
openspec validate close-demo-readiness --type change --strict
openspec validate --all
git diff --check
git add openspec/changes/close-demo-readiness
git commit -m "docs(openspec): 规划技术 Demo P0 P1 收口"
```

Expected: change 严格校验通过；全量 OpenSpec 通过；提交只包含新 change artifacts。

---

### Task 3: 用 TDD 收口双发布资产、LICENSE 与干净 clone 包测试

**Files:**
- Create: `LICENSE`
- Modify: `scripts/package_anp_release.py`
- Modify: `tests/test_package_anp_release.py`
- Modify: `tests/test_anp_dependency_versions.py`
- Modify: `plugins/anp-agent/tests/test_packaging.py`

**Interfaces:**
- Consumes: `package_release(root: Path | None, dist_dir: Path | None, version: str) -> list[Path]`。
- Produces: `package_release(...)` 返回 `[plugin_versioned, plugin_alias, client_versioned, client_alias]`；四个文件均存在，alias 与对应版本化文件字节一致，归档包含 `LICENSE`。

- [ ] **Step 1: 修改根级打包测试，先要求四个资产和 LICENSE**

Replace `test_package_release_creates_exact_plugin_and_skill_archives` in `tests/test_package_anp_release.py` with:

```python
def test_package_release_creates_versioned_and_stable_archives(
    tmp_path: Path,
) -> None:
    """打包脚本生成版本化资产、稳定别名和 LICENSE。"""
    packager = _load_packager()

    result = packager.package_release(root=ROOT, dist_dir=tmp_path, version="9.9.9")

    plugin_zip = tmp_path / "anp-agent-plugin-9.9.9.zip"
    plugin_alias = tmp_path / "anp-agent.zip"
    skill_zip = tmp_path / "anp-client-skill-9.9.9.zip"
    skill_alias = tmp_path / "anp-client.zip"
    assert result == [plugin_zip, plugin_alias, skill_zip, skill_alias]
    assert plugin_alias.read_bytes() == plugin_zip.read_bytes()
    assert skill_alias.read_bytes() == skill_zip.read_bytes()

    with zipfile.ZipFile(plugin_zip) as archive:
        assert archive.namelist() == [
            "README.md",
            "__init__.py",
            "plugin.yaml",
            "pyproject.toml",
            "anp_agent/__init__.py",
            "anp_agent/adapter.py",
            "anp_agent/auth.py",
            "anp_agent/bridge.py",
            "anp_agent/config.py",
            "anp_agent/constants.py",
            "anp_agent/identity.py",
            "anp_agent/server.py",
            "anp_agent/tools.py",
            "LICENSE",
        ]
        assert "MIT License" in archive.read("LICENSE").decode()
        assert "本地 DID resolver base URL" in archive.read("plugin.yaml").decode()

    with zipfile.ZipFile(skill_zip) as archive:
        assert archive.namelist() == [
            "README.md",
            "SKILL.md",
            "requirements.txt",
            "scripts/anp_client.py",
            "scripts/did_identity.py",
            "scripts/did_server.py",
            "scripts/signing.py",
            "LICENSE",
        ]
        assert "MIT License" in archive.read("LICENSE").decode()
        assert "loopback_endpoints_equivalent" in archive.read(
            "scripts/anp_client.py"
        ).decode()
```

- [ ] **Step 2: 修改插件包化测试，先要求临时构建稳定插件包**

Add below `PLUGIN_ROOT` in `plugins/anp-agent/tests/test_packaging.py`:

```python
REPO_ROOT = PLUGIN_ROOT.parents[1]
PACKAGER_PATH = REPO_ROOT / "scripts" / "package_anp_release.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("plugin_test_packager", PACKAGER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

Replace the release zip test with:

```python
def test_release_zip_contains_packaged_plugin_root_only(tmp_path: Path):
    """干净 clone 中临时构建的稳定插件包结构正确。"""
    packager = _load_packager()
    packager.package_release(root=REPO_ROOT, dist_dir=tmp_path, version="9.9.9")
    zip_path = tmp_path / "anp-agent.zip"

    with zipfile.ZipFile(zip_path) as archive:
        names = [name.rstrip("/") for name in archive.namelist()]

    assert "plugin.yaml" in names
    assert "__init__.py" in names
    assert "README.md" in names
    assert "pyproject.toml" in names
    assert "LICENSE" in names
    assert any(name == "anp_agent" or name.startswith("anp_agent/") for name in names)

    for name in names:
        path = Path(name)
        assert not any(part in FORBIDDEN_ZIP_PARTS for part in path.parts)
        assert path.name not in FORBIDDEN_ZIP_NAMES
        assert not path.name.endswith(".pem")
        assert ".bak." not in path.name
```

- [ ] **Step 3: 运行 RED 测试**

Run:

```bash
cd /home/peter/anp-hermes
python3 -m pytest tests/test_package_anp_release.py::test_package_release_creates_versioned_and_stable_archives -q
cd plugins/anp-agent
python3 -m pytest tests/test_packaging.py::test_release_zip_contains_packaged_plugin_root_only -q
```

Expected: FAIL，因为当前 `package_release` 只返回两个版本化文件，且归档中没有 `LICENSE` 或稳定别名。

- [ ] **Step 4: 添加标准 MIT LICENSE**

Create `LICENSE`:

```text
MIT License

Copyright (c) 2026 ANP Hermes Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: 实现四资产打包**

In `scripts/package_anp_release.py`:

1. Add import:

```python
import shutil
```

2. Replace `_write_archive` with:

```python
def _write_archive(
    archive_path: Path,
    source_root: Path,
    files: list[str],
    license_path: Path,
) -> None:
    """按固定文件清单写入 zip，并在归档根加入 LICENSE。"""
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for relative in files:
            source = source_root / relative
            if not source.is_file():
                raise FileNotFoundError(f"缺少发布文件: {source}")
            archive.write(source, relative)
        if not license_path.is_file():
            raise FileNotFoundError(f"缺少许可证文件: {license_path}")
        archive.write(license_path, "LICENSE")
```

3. Replace the archive construction block in `package_release` with:

```python
    plugin_zip = output_dir / f"anp-agent-plugin-{version}.zip"
    plugin_alias = output_dir / "anp-agent.zip"
    skill_zip = output_dir / f"anp-client-skill-{version}.zip"
    skill_alias = output_dir / "anp-client.zip"
    license_path = repo_root / "LICENSE"

    _write_archive(
        plugin_zip,
        repo_root / "plugins" / "anp-agent",
        PLUGIN_FILES,
        license_path,
    )
    _write_archive(
        skill_zip,
        repo_root / "clients" / "anp-client",
        SKILL_FILES,
        license_path,
    )
    shutil.copyfile(plugin_zip, plugin_alias)
    shutil.copyfile(skill_zip, skill_alias)

    archives = [plugin_zip, plugin_alias, skill_zip, skill_alias]
    errors = [error for archive in archives for error in validate_archive(archive)]
    if errors:
        raise RuntimeError("\n".join(errors))

    return archives
```

- [ ] **Step 6: 让依赖测试适用于干净 clone**

In `tests/test_anp_dependency_versions.py`, add:

```python
from importlib.metadata import version
```

Replace `test_upstream_anp_source_version_is_current_baseline` with:

```python
def test_installed_anp_version_satisfies_current_baseline() -> None:
    """当前验证环境安装的 ANP SDK 满足项目版本边界。"""
    installed = tuple(int(part) for part in version("anp").split(".")[:3])

    assert (0, 8, 9) <= installed < (0, 9, 0)
```

This removes the hard-coded `/home/peter/agent-network-protocol/anp/pyproject.toml` dependency.

- [ ] **Step 7: 运行 GREEN 测试**

Run:

```bash
cd /home/peter/anp-hermes
python3 -m pytest tests/ -q
cd plugins/anp-agent
python3 -m pytest tests/test_packaging.py -q
```

Expected: 根级测试和插件包化测试全部通过；不需要仓库中预先存在 zip。

- [ ] **Step 8: 检查实际四资产内容**

Run:

```bash
DIST_DIR="$(mktemp -d /tmp/anp-demo-package.XXXXXX)"
cd /home/peter/anp-hermes
python3 scripts/package_anp_release.py --dist-dir "$DIST_DIR"
python3 - "$DIST_DIR" <<'PY'
from pathlib import Path
from zipfile import ZipFile
import sys

root = Path(sys.argv[1])
expected = {
    "anp-agent-plugin-0.1.0.zip",
    "anp-agent.zip",
    "anp-client-skill-0.1.0.zip",
    "anp-client.zip",
}
assert {path.name for path in root.iterdir()} == expected
assert (root / "anp-agent.zip").read_bytes() == (
    root / "anp-agent-plugin-0.1.0.zip"
).read_bytes()
assert (root / "anp-client.zip").read_bytes() == (
    root / "anp-client-skill-0.1.0.zip"
).read_bytes()
for name in expected:
    with ZipFile(root / name) as archive:
        assert "LICENSE" in archive.namelist()
print("四个发布资产与 LICENSE 验证通过")
PY
rm -rf "$DIST_DIR"
```

Expected: `四个发布资产与 LICENSE 验证通过`。

- [ ] **Step 9: 提交打包与许可证变更**

Run:

```bash
git add LICENSE scripts/package_anp_release.py tests/test_package_anp_release.py tests/test_anp_dependency_versions.py plugins/anp-agent/tests/test_packaging.py
git commit -m "feat: 收口 ANP Demo 发布包与许可证"
```

Expected: 一个自包含的打包/许可证提交。

---

### Task 4: 修复动态端口、Black 与 Ruff 已知门禁

**Files:**
- Modify: `plugins/anp-agent/tests/test_adapter.py`
- Modify: `plugins/anp-agent/tests/e2e/conftest.py`
- Modify: `scripts/verify_anp_sdk.py`

**Interfaces:**
- Consumes: `load_config(platform_config)` 的 `extra` 配置优先级；Black 100 字符行宽；Ruff F401。
- Produces: adapter 连接测试固定使用 `port=0`；项目目标路径的 Ruff/Black clean。

- [ ] **Step 1: 添加动态端口回归测试**

In `plugins/anp-agent/tests/test_adapter.py`, add after `platform_config` fixture:

```python
def test_platform_config_uses_dynamic_port(platform_config):
    """适配器连接测试不得占用默认 8900 端口。"""
    from anp_agent.config import load_config

    assert load_config(platform_config).port == 0
```

- [ ] **Step 2: 运行 RED 测试**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python3 -m pytest tests/test_adapter.py::test_platform_config_uses_dynamic_port -q
```

Expected: FAIL，当前 fixture 未指定 port，加载结果为默认 `8900`。

- [ ] **Step 3: 最小修改 fixture**

Replace `platform_config` fixture body with:

```python
@pytest.fixture
def platform_config(tmp_path):
    class PlatformConfig:
        extra = {
            "host": "127.0.0.1",
            "port": 0,
            "hostname": "localhost",
            "endpoint": "http://localhost:0",
            "data_dir": str(tmp_path / "adapter"),
        }

    return PlatformConfig()
```

- [ ] **Step 4: 运行 adapter GREEN 测试，同时保留用户 Hermes**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python3 -m pytest tests/test_adapter.py -q
```

Expected: adapter 测试全部通过，即使本机 8900 已被 Hermes 占用；不得终止现有 Hermes 进程。

- [ ] **Step 5: 用 Black 修复已知 E2E fixture 格式**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
black tests/e2e/conftest.py
black --check tests/e2e/conftest.py
```

Expected: 第一次命令只重排 `pytest.skip(...)` 行；第二次退出 0。

- [ ] **Step 6: 清理 verify_anp_sdk.py 未使用导入和过期路径**

Make these exact edits in `scripts/verify_anp_sdk.py`:

- Replace docstring run example:

```text
运行方式：
    python3 scripts/verify_anp_sdk.py
```

- Remove:

```python
import aiohttp
```

- Replace Hermes import block with:

```python
        from gateway.platforms.base import BasePlatformAdapter
        from hermes_cli.plugins import PluginContext
```

Do not change the contract assertions or runtime behavior.

- [ ] **Step 7: 运行静态门禁**

Run:

```bash
cd /home/peter/anp-hermes
ruff check scripts tests clients/anp-client plugins/anp-agent
black --check scripts tests clients/anp-client plugins/anp-agent
```

Expected: 两条命令均退出 0。

- [ ] **Step 8: 运行受影响测试并提交**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python3 -m pytest tests/test_adapter.py tests/e2e/test_fixtures.py -q
cd /home/peter/anp-hermes
git add plugins/anp-agent/tests/test_adapter.py plugins/anp-agent/tests/e2e/conftest.py scripts/verify_anp_sdk.py
git commit -m "fix: 收口 ANP Demo 本地质量门禁"
```

Expected: 受影响测试通过；提交只包含三个文件。

---

### Task 5: 将 GitHub Actions 改为 master 单版本完整门禁

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: 根级、客户端和插件现有命令；npm package `@fission-ai/openspec@1.5.0`。
- Produces: `master` push/PR 上运行的单一 Python 3.12 `demo` job。

- [ ] **Step 1: 先验证当前 workflow 缺口**

Run:

```bash
cd /home/peter/anp-hermes
python3 - <<'PY'
from pathlib import Path

text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
assert "branches: [master" in text, "CI 尚未监听 master"
assert 'python-version: "3.12"' in text, "CI 尚未固定 Python 3.12"
assert "openspec validate --all" in text, "CI 尚未校验 OpenSpec"
assert "clients/anp-client/tests" in text, "CI 尚未运行客户端测试"
assert "scripts/package_anp_release.py" in text, "CI 尚未构建发布包"
PY
```

Expected: FAIL，至少显示 `CI 尚未监听 master`。

- [ ] **Step 2: 用最小完整 workflow 替换 ci.yml**

Replace `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
    branches: [master, feature/*]
  pull_request:
    branches: [master]

jobs:
  demo:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e "./plugins/anp-agent[test,dev]"
          python -m pip install -r clients/anp-client/requirements-dev.txt
          npm install --global @fission-ai/openspec@1.5.0

      - name: Validate OpenSpec
        run: openspec validate --all

      - name: Run root tests
        run: python -m pytest tests/ -q

      - name: Run client tests
        run: python -m pytest clients/anp-client/tests/ -q

      - name: Run Ruff
        run: ruff check scripts tests clients/anp-client plugins/anp-agent

      - name: Run Black
        run: black --check scripts tests clients/anp-client plugins/anp-agent

      - name: Build release archives
        run: python scripts/package_anp_release.py

      - name: Run plugin tests
        working-directory: plugins/anp-agent
        run: python -m pytest tests/ -q

      - name: Check plugin coverage
        working-directory: plugins/anp-agent
        run: python -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

- [ ] **Step 3: 验证 workflow 结构和关键命令**

Run:

```bash
cd /home/peter/anp-hermes
python3 - <<'PY'
from pathlib import Path
import yaml

path = Path(".github/workflows/ci.yml")
text = path.read_text(encoding="utf-8")
data = yaml.safe_load(text)
assert isinstance(data, dict)
assert "branches: [master, feature/*]" in text
assert "branches: [master]" in text
assert 'python-version: "3.12"' in text
assert "openspec validate --all" in text
assert "python -m pytest tests/ -q" in text
assert "python -m pytest clients/anp-client/tests/ -q" in text
assert "ruff check scripts tests clients/anp-client plugins/anp-agent" in text
assert "black --check scripts tests clients/anp-client plugins/anp-agent" in text
assert "python scripts/package_anp_release.py" in text
assert "--cov=anp_agent --cov-fail-under=85" in text
print("CI 结构检查通过")
PY
```

Expected: `CI 结构检查通过`。

- [ ] **Step 4: 验证 OpenSpec npm 安装命令可用**

Run:

```bash
npx --yes @fission-ai/openspec@1.5.0 --version
```

Expected: 输出 `1.5.0`。若网络不可用，记录为 CI 外部安装待推送后验证，不得声称 GitHub Actions 已实际通过；不要改成未固定版本。

- [ ] **Step 5: 本地按 workflow 顺序运行快速门禁**

Run:

```bash
cd /home/peter/anp-hermes
openspec validate --all
python3 -m pytest tests/ -q
python3 -m pytest clients/anp-client/tests/ -q
ruff check scripts tests clients/anp-client plugins/anp-agent
black --check scripts tests clients/anp-client plugins/anp-agent
DIST_DIR="$(mktemp -d /tmp/anp-ci-package.XXXXXX)"
python3 scripts/package_anp_release.py --dist-dir "$DIST_DIR"
rm -rf "$DIST_DIR"
cd plugins/anp-agent
python3 -m pytest tests/ -q
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

Expected: 所有本地等价门禁通过。此步骤不等价于远端 Actions 运行，最终报告必须如实说明未推送。

- [ ] **Step 6: 提交 CI 变更**

Run:

```bash
cd /home/peter/anp-hermes
git add .github/workflows/ci.yml
git commit -m "ci: 收口技术 Demo 单版本门禁"
```

Expected: 一个只修改 CI workflow 的提交。

---

### Task 6: 同步 README、插件 README 与发布说明

**Files:**
- Modify: `README.md`
- Modify: `plugins/anp-agent/README.md`

**Interfaces:**
- Consumes: Task 3 的四资产命名、LICENSE 和干净 clone 包测试；Task 5 的 CI 命令。
- Produces: 不宣称已有 Release、无需手工复制 ignored zip、链接 MIT LICENSE 的用户入口文档。

- [ ] **Step 1: 更新根 README 的测试命令**

In `README.md`, replace the plugin test preamble and commands at the “Hermes 服务端插件” subsection with:

```markdown
### Hermes 服务端插件

插件普通测试会在临时目录构建并检查发布 zip，因此干净 clone 不需要预先准备 ignored `anp-agent.zip`：

```bash
cd plugins/anp-agent

# 单元测试与集成测试
python3 -m pytest tests/ -q

# 覆盖率检查（要求 ≥ 85%）
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q

# 格式与 lint
ruff check .
black --check .

# 确定性 Echo E2E：使用本地 mock LLM，无需真实 API key
python3 -m pytest tests/e2e/test_echo.py -v --run-e2e

# 真实 LLM E2E：使用 Hermes 配置的 provider，满足前置条件时运行
python3 -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```
```

Keep the existing paragraph that describes real LLM prerequisites; do not claim it was rerun in this change.

- [ ] **Step 2: 更新根 README 的四资产列表和许可证**

Replace the release asset list with:

```markdown
脚本会生成并校验：

- `dist/anp-agent-plugin-0.1.0.zip` — 版本化 Hermes 插件包
- `dist/anp-agent.zip` — 稳定插件别名
- `dist/anp-client-skill-0.1.0.zip` — 版本化客户端 skill 包
- `dist/anp-client.zip` — 稳定客户端别名

稳定别名与对应版本化资产内容相同。两个逻辑发布包都包含仓库根 MIT `LICENSE`；发布包由固定文件 allowlist 构建，并会检查运行态 DID 文件、PEM/pyc 后缀、缓存目录、已知本机路径引用和私钥块。
```

Replace the final license section with:

```markdown
## 许可证

[MIT](LICENSE)
```

- [ ] **Step 3: 修正插件 README 的 Release 表述**

Replace `plugins/anp-agent/README.md` “对话框安装（推荐）” opening with:

```markdown
### 对话框安装（发布 Release 后）

仓库创建 GitHub Release 并上传稳定资产 `anp-agent.zip` 后，可以在 Hermes 对话框中发送：

```text
安装插件 https://github.com/Jasper-1222/anp-hermes/releases/latest/download/anp-agent.zip
```

当前源码仓库尚未创建 Release；本地体验请使用下方手动安装，或运行仓库根 `python3 scripts/package_anp_release.py` 生成 `dist/anp-agent.zip`。
```

Keep the existing six installation steps after this block.

- [ ] **Step 4: 更新插件 README 的测试前置条件**

Ensure the plugin README says:

```markdown
普通测试会通过根发布脚本在临时目录生成并检查 zip，不要求源码目录预先存在 ignored `anp-agent.zip`。从仓库根运行完整打包可得到版本化文件和稳定别名：

```bash
python3 scripts/package_anp_release.py
```
```

Remove any instruction that requires manually copying `dist/anp-agent-plugin-0.1.0.zip` to `plugins/anp-agent/anp-agent.zip` before ordinary tests.

- [ ] **Step 5: 运行 README 事实检查**

Run:

```bash
cd /home/peter/anp-hermes
python3 - <<'PY'
from pathlib import Path

root = Path("README.md").read_text(encoding="utf-8")
plugin = Path("plugins/anp-agent/README.md").read_text(encoding="utf-8")
for item in [
    "ANP × Hermes 技术验证 Demo",
    "anp-agent-plugin-0.1.0.zip",
    "anp-agent.zip",
    "anp-client-skill-0.1.0.zip",
    "anp-client.zip",
    "[MIT](LICENSE)",
]:
    assert item in root, item
assert "当前源码仓库尚未创建 Release" in plugin
assert "releases/latest/download/anp-agent.zip" in plugin
assert "cp dist/anp-agent-plugin-0.1.0.zip" not in root
assert "cp dist/anp-agent-plugin-0.1.0.zip" not in plugin
print("README 事实检查通过")
PY
git diff --check -- README.md plugins/anp-agent/README.md
```

Expected: `README 事实检查通过`，空白检查无输出。

- [ ] **Step 6: 提交用户入口文档**

Run:

```bash
git add README.md plugins/anp-agent/README.md
git commit -m "docs: 同步技术 Demo 测试与发布说明"
```

Expected: 一个只包含两个 README 的提交。

---

### Task 7: 同步 CLAUDE.md、进展文档与 anp-client Purpose

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/anp-hermes-openspec-execution-state.md`
- Modify: `docs/anp-hermes-openspec-roadmap.md`
- Modify: `docs/anp-hermes-current-implementation-analysis.md`
- Modify: `openspec/specs/anp-client-skill/spec.md`

**Interfaces:**
- Consumes: 当前 active change `close-demo-readiness`、17 个此前归档变更、Task 3-6 的实际实现。
- Produces: 归档前事实一致的开发者文档；正式 `anp-client-skill` Purpose。`anp-community-readiness` 暂不手工修改，留给 Task 9 的 OpenSpec archive 同步。

- [ ] **Step 1: 更新 CLAUDE.md 的项目目标和命令**

Add this sentence to `## 项目目标` after the first paragraph:

```markdown
当前交付定位是可公开体验、可重复验证的 ANP × Hermes 技术 Demo；本轮不以生产部署、限流、持久化审计或跨机器 DID 托管为目标。
```

Extend `## 常用命令` with exact root/client commands:

```bash
# 仓库根级依赖与发布测试
python3 -m pytest tests/ -q

# ANP 调用端 skill
python3 -m pytest clients/anp-client/tests/ -q
ruff check clients/anp-client
black --check clients/anp-client

# 构建版本化包与稳定别名
python3 scripts/package_anp_release.py
```

Keep existing plugin and E2E commands.

- [ ] **Step 2: 更新 CLAUDE.md 的 OpenSpec 状态和仓库结构**

During apply, use this status block:

```markdown
## OpenSpec 当前状态

- `close-demo-readiness` 之前共有 17 个变更完成、同步并归档。
- 当前唯一 active change 为 `close-demo-readiness`，用于收口技术 Demo 的 CI、发布包、许可证和文档事实一致性。
- 完成后必须同步 main specs、归档该 change，并确认 active changes 恢复为空。
- main specs 当前包含 16 个 capability specs。
```

Extend the structure tree with:

```text
├── clients/anp-client/       # ANP 调用端 skill：身份、DID 服务、发现与签名 chat
├── scripts/                  # SDK 验证与 plugin/client 发布包构建
├── tests/                    # 根级依赖和发布包测试
```

Do not remove existing plugin structure or security gotchas.

- [ ] **Step 3: 替换执行状态文档顶部过期状态**

In `docs/anp-hermes-openspec-execution-state.md`:

- Set date to `2026-07-15`.
- Replace the top “当前状态” and duplicate “当前 active change” text with:

```markdown
## 当前状态

`close-demo-readiness` 之前共有 17 个 OpenSpec 变更完成、同步并归档，覆盖初始插件、对话框安装、E2E、认证错误、Top 10 收口、社区就绪审计、ANP client skill 和 ANP SDK 0.8.9 基线更新。

当前唯一 active change：

```text
close-demo-readiness
```

状态：正在收口技术 Demo 的社区 README、master CI、最低质量门禁、MIT LICENSE、双发布资产和文档事实一致性。本变更不实现生产部署、Bearer 扩展、限流、持久化审计、跨机器 DID、AP2 或 E2EE。
```

Preserve historical completed and verification records below; remove every statement that says `review-community-readiness` is currently active or should be entered next.

- [ ] **Step 4: 更新路线图为 Demo 收口状态**

In `docs/anp-hermes-openspec-roadmap.md`:

- Set the top status to:

```markdown
状态：初始能力、Top 10、社区就绪审计、ANP client skill、发布打包和 ANP SDK 0.8.9 基线均已完成；当前执行技术 Demo P0/P1 收口。
```

- Mark `review-community-readiness` as completed and archived.
- Add a completed extension section containing `add-anp-client-skill` and `update-anp-sdk-dependency`.
- Replace the detailed future backlog with:

```markdown
## 当前不实施范围

本项目当前以技术 Demo 为完成目标。生产部署、Bearer 后续请求、per-DID 限流、持久化审计、resolver 上游改造、跨机器 DID 托管、AP2 和 E2EE 保留为可选后续主题，不属于 `close-demo-readiness`，也不阻塞本轮完成。
```

Do not create tasks or schedules for these P2 topics.

- [ ] **Step 5: 更新当前实现分析**

In `docs/anp-hermes-current-implementation-analysis.md`:

- Set date/status to 2026-07-15 and技术 Demo P0/P1 收口中。
- Add current implemented facts: `clients/anp-client/`, four release assets, ANP SDK `>=0.8.9,<0.9.0`.
- Replace the audit claim with:

```markdown
工具执行器支持注入不记录完整参数/结果的安全审计回调；当前默认 server 未配置 audit sink，因此默认不输出或持久化审计事件。持久化审计不属于本技术 Demo 的当前范围。
```

- Update validation baseline to include root tests, client tests and four-asset packaging.
- Remove “先完成 review-community-readiness” and replace final recommendation with:

```markdown
完成 `close-demo-readiness` 的本地验证、main specs 同步和归档后，项目即可保持技术 Demo 状态供社区体验；本轮不要求继续推进生产化 backlog。
```

- Keep historical real LLM statement, but explicitly say it was not rerun in this change.

- [ ] **Step 6: 填写 anp-client-skill 正式 Purpose**

Replace `openspec/specs/anp-client-skill/spec.md:3-5` with:

```markdown
## Purpose

定义可独立安装的 ANP 调用端 skill，使个人智能体能够管理 DID WBA 身份、在本地提供 DID 文档、发现 ANP 服务智能体并发送签名 `chat` 请求，同时约束 endpoint 安全、安装包边界和第一期非目标。
```

Do not modify its requirements.

- [ ] **Step 7: 运行文档状态检查**

Run:

```bash
cd /home/peter/anp-hermes
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("CLAUDE.md"),
    Path("docs/anp-hermes-openspec-execution-state.md"),
    Path("docs/anp-hermes-openspec-roadmap.md"),
    Path("docs/anp-hermes-current-implementation-analysis.md"),
]
texts = {path: path.read_text(encoding="utf-8") for path in paths}
for path, text in texts.items():
    assert "close-demo-readiness" in text, path
    assert "review-community-readiness` apply 进行中" not in text, path
assert "TBD - created by archiving" not in Path(
    "openspec/specs/anp-client-skill/spec.md"
).read_text(encoding="utf-8")
assert "当前默认 server 未配置 audit sink" in texts[
    Path("docs/anp-hermes-current-implementation-analysis.md")
]
print("归档前文档状态检查通过")
PY
openspec validate --all
git diff --check
```

Expected: `归档前文档状态检查通过`；OpenSpec 全量通过；空白检查无输出。

- [ ] **Step 8: 提交归档前事实同步**

Run:

```bash
git add CLAUDE.md docs/anp-hermes-openspec-execution-state.md docs/anp-hermes-openspec-roadmap.md docs/anp-hermes-current-implementation-analysis.md openspec/specs/anp-client-skill/spec.md
git commit -m "docs: 同步技术 Demo 当前执行状态"
```

Expected: 文档提交不包含 `anp-community-readiness` 手工修改。

---

### Task 8: 运行实现完成门禁并修复本轮回归

**Files:**
- Modify only if a verification failure is caused by Tasks 3-7.
- Update: `openspec/changes/close-demo-readiness/tasks.md` after proof exists.

**Interfaces:**
- Consumes: Tasks 1-7 的全部提交。
- Produces: 代码/文档归档前的完整通过证据；tasks 5.1 和各实现项可据实勾选。

- [ ] **Step 1: 运行 OpenSpec、静态检查和空白门禁**

Run:

```bash
cd /home/peter/anp-hermes
openspec validate close-demo-readiness --type change --strict
openspec validate --all
ruff check scripts tests clients/anp-client plugins/anp-agent
black --check scripts tests clients/anp-client plugins/anp-agent
git diff --check master...HEAD
```

Expected: 全部退出 0。

- [ ] **Step 2: 运行根级与客户端测试**

Run:

```bash
cd /home/peter/anp-hermes
python3 -m pytest tests/ -q
python3 -m pytest clients/anp-client/tests/ -q
```

Expected: 两个测试集 0 failed。

- [ ] **Step 3: 运行四资产临时打包**

Run:

```bash
DIST_DIR="$(mktemp -d /tmp/anp-demo-final-package.XXXXXX)"
cd /home/peter/anp-hermes
python3 scripts/package_anp_release.py --dist-dir "$DIST_DIR"
test -f "$DIST_DIR/anp-agent-plugin-0.1.0.zip"
test -f "$DIST_DIR/anp-agent.zip"
test -f "$DIST_DIR/anp-client-skill-0.1.0.zip"
test -f "$DIST_DIR/anp-client.zip"
rm -rf "$DIST_DIR"
```

Expected: 打包命令输出四个“已生成”路径，四个 `test -f` 均通过。

- [ ] **Step 4: 运行插件普通测试和覆盖率**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python3 -m pytest tests/ -q
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
```

Expected: 普通测试 0 failed；覆盖率不少于 85%。不得通过 `ANP_PORT=0` 全局覆盖绕过配置测试，因为 adapter fixture 已独立修复。

- [ ] **Step 5: 运行本地无凭据 E2E**

Run:

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python3 -m pytest tests/e2e/ -q --run-e2e
```

Expected: mock/fixture/client E2E 通过；真实 LLM 用例因缺少 `--run-slow-e2e` 按预期 skip。不得声称真实 LLM 在本轮重新通过。

- [ ] **Step 6: 若失败，限定修复范围并复跑原命令**

For every failure:

1. Invoke `superpowers:systematic-debugging` before editing.
2. Only modify a file changed by this plan or the minimum directly related test/config file.
3. Re-run the exact failed command until it exits 0.
4. Do not skip tests, reduce coverage, remove assertions, or stop the user's Hermes process.
5. Commit the minimal fix with a Chinese `fix:` message.

- [ ] **Step 7: 根据实际证据勾选 tasks 1.1 至 5.1**

Edit `openspec/changes/close-demo-readiness/tasks.md` so completed implementation and verification items through `5.1` use `- [x]`。保持 `5.2`（干净 clone）、`5.3`（归档）和 `5.4`（最终状态）未勾选。

Run:

```bash
openspec validate close-demo-readiness --type change --strict
git add openspec/changes/close-demo-readiness/tasks.md
git commit -m "test: 完成技术 Demo 收口验证矩阵"
```

Expected: change 仍严格有效；提交记录归档前验证进度。

---

### Task 9: 运行干净 clone smoke、同步 main specs 并归档 OpenSpec

**Files:**
- Modify through archive: `openspec/specs/anp-plugin-packaging/spec.md`
- Modify through archive: `openspec/specs/anp-test-harness/spec.md`
- Modify through archive: `openspec/specs/anp-community-readiness/spec.md`
- Move through archive: `openspec/changes/close-demo-readiness/` → `openspec/changes/archive/2026-07-15-close-demo-readiness/`
- Modify: `CLAUDE.md`
- Modify: `docs/anp-hermes-openspec-execution-state.md`
- Modify: `docs/anp-hermes-openspec-roadmap.md`
- Modify: `docs/anp-hermes-current-implementation-analysis.md`

**Interfaces:**
- Consumes: 通过完整本地门禁的 `close-demo-readiness` change。
- Produces: 三个更新后的 main specs、归档 change、active changes 为空、最终状态文档。

- [ ] **Step 1: 提交当前实现，确保 clean clone 包含全部内容**

Run:

```bash
cd /home/peter/anp-hermes
git status --short --branch
git log -8 --oneline --decorate
```

Expected: 除 `?? .claude/worktrees/` 外无未提交内容。若有本轮已验证但未提交的修改，按所属任务补提交后再继续。

- [ ] **Step 2: 在临时 clone 执行 smoke 验证**

Run:

```bash
SOURCE=/home/peter/anp-hermes
SMOKE_ROOT="$(mktemp -d /tmp/anp-demo-clean-clone.XXXXXX)"
git clone --local --no-hardlinks "$SOURCE" "$SMOKE_ROOT/repo"
python3 -m venv --system-site-packages "$SMOKE_ROOT/venv"
"$SMOKE_ROOT/venv/bin/python" -m pip install --no-deps -e "$SMOKE_ROOT/repo/plugins/anp-agent"
cd "$SMOKE_ROOT/repo"
openspec validate --all
"$SMOKE_ROOT/venv/bin/python" -m pytest tests/ -q
"$SMOKE_ROOT/venv/bin/python" -m pytest clients/anp-client/tests/ -q
"$SMOKE_ROOT/venv/bin/python" scripts/package_anp_release.py --dist-dir "$SMOKE_ROOT/dist"
cd plugins/anp-agent
"$SMOKE_ROOT/venv/bin/python" -m pytest tests/ -q
cd "$SOURCE"
rm -rf "$SMOKE_ROOT"
```

Expected: 临时 clone 中 OpenSpec、根级、客户端、四资产打包和插件普通测试全部通过；没有依赖 `/home/peter/agent-network-protocol` 或预生成 zip。

- [ ] **Step 3: 勾选干净 clone 任务并严格校验**

Mark `5.2` complete in `openspec/changes/close-demo-readiness/tasks.md`.

Run:

```bash
cd /home/peter/anp-hermes
openspec validate close-demo-readiness --type change --strict
```

Expected: strict validation passes.

- [ ] **Step 4: 归档并同步 main specs**

Run:

```bash
openspec archive close-demo-readiness -y
```

Expected:

- change moved to `openspec/changes/archive/2026-07-15-close-demo-readiness/`；
- deltas merged into `anp-plugin-packaging`、`anp-test-harness`、`anp-community-readiness` main specs；
- command exits 0 without `--skip-specs` or `--no-validate`。

- [ ] **Step 5: 将归档 tasks 的 5.3 与 5.4 标记完成**

Edit `openspec/changes/archive/2026-07-15-close-demo-readiness/tasks.md`:

```markdown
- [x] 5.3 同步 delta specs 并归档 `close-demo-readiness`。
- [x] 5.4 确认 active changes 为空并记录最终验证结果。
```

Only mark `5.4` after the next command confirms an empty active list.

- [ ] **Step 6: 更新最终无 active change 文档状态**

Run first:

```bash
openspec list --json
```

Expected: `"changes": []`。

Then update the current-state sections in `CLAUDE.md` and the three progress documents to say:

```markdown
- 截至 2026-07-15，共 18 个 OpenSpec 变更完成、同步并归档。
- 当前 active changes 为空。
- `close-demo-readiness` 已完成技术 Demo 的社区 README、master CI、最低质量门禁、MIT LICENSE、双发布资产和文档事实一致性收口。
- 当前项目可保持技术 Demo 状态供社区体验；P2 和生产化能力不属于本轮完成条件。
```

Remove wording that says `close-demo-readiness` is currently applying. Preserve historical sections.

- [ ] **Step 7: 校验归档结果和 main specs**

Run:

```bash
openspec list --json
openspec validate --all
python3 - <<'PY'
from pathlib import Path

assert Path("openspec/changes/archive/2026-07-15-close-demo-readiness").is_dir()
for path in [
    Path("openspec/specs/anp-plugin-packaging/spec.md"),
    Path("openspec/specs/anp-test-harness/spec.md"),
    Path("openspec/specs/anp-community-readiness/spec.md"),
]:
    text = path.read_text(encoding="utf-8")
    assert "技术 Demo" in text, path
assert "TBD - created by archiving" not in Path(
    "openspec/specs/anp-client-skill/spec.md"
).read_text(encoding="utf-8")
print("OpenSpec 归档与 main specs 检查通过")
PY
git diff --check
```

Expected: active changes 为空；全部 specs/changes 校验通过；脚本输出 `OpenSpec 归档与 main specs 检查通过`。

- [ ] **Step 8: 提交 OpenSpec 归档与最终状态**

Run:

```bash
git add CLAUDE.md docs/anp-hermes-openspec-execution-state.md docs/anp-hermes-openspec-roadmap.md docs/anp-hermes-current-implementation-analysis.md openspec/specs openspec/changes/archive/2026-07-15-close-demo-readiness openspec/changes/close-demo-readiness
git commit -m "docs(openspec): 归档技术 Demo P0 P1 收口"
```

Expected: Git records change deletion/move、main spec updates、tasks final completion和最终状态文档。

---

### Task 10: 最终验证与交付检查

**Files:**
- Verification only; do not change files unless a regression is proven.

**Interfaces:**
- Consumes: 已归档且提交的统一收口分支。
- Produces: 可引用的最终本地验证证据和无外部发布动作的交付状态。

- [ ] **Step 1: 复跑最终 OpenSpec、测试与静态门禁**

Run:

```bash
set -e
cd /home/peter/anp-hermes
openspec list --json
openspec validate --all
python3 -m pytest tests/ -q
python3 -m pytest clients/anp-client/tests/ -q
ruff check scripts tests clients/anp-client plugins/anp-agent
black --check scripts tests clients/anp-client plugins/anp-agent
DIST_DIR="$(mktemp -d /tmp/anp-demo-release-final.XXXXXX)"
python3 scripts/package_anp_release.py --dist-dir "$DIST_DIR"
rm -rf "$DIST_DIR"
cd plugins/anp-agent
python3 -m pytest tests/ -q
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
python3 -m pytest tests/e2e/ -q --run-e2e
cd /home/peter/anp-hermes
git diff --check master...HEAD
```

Expected:

- active changes 为空；
- OpenSpec 全量 0 failed；
- 根级、客户端、插件和本地 E2E 0 failed；
- coverage `>=85%`；
- Ruff/Black 退出 0；
- 四个发布资产成功生成；
- diff whitespace clean。

- [ ] **Step 2: 检查提交、工作区和分支边界**

Run:

```bash
cd /home/peter/anp-hermes
git status --short --branch
git log --graph --oneline --decorate master..HEAD
git tag --list
git remote -v
```

Expected:

- 当前分支为 `chore/close-demo-readiness`；
- 除本地 `.claude/worktrees/` 外无未提交文件；
- 历史包含 README 保全 merge、OpenSpec、打包/LICENSE、质量、CI、文档同步、验证和归档提交；
- 本计划未创建新 tag；
- 未执行 push。

- [ ] **Step 3: 检查没有 P2 实现或虚假发布声明**

Run:

```bash
python3 - <<'PY'
from pathlib import Path

readme = Path("README.md").read_text(encoding="utf-8")
plugin = Path("plugins/anp-agent/README.md").read_text(encoding="utf-8")
assert "当前源码仓库尚未创建 Release" in plugin
assert "[MIT](LICENSE)" in readme
assert Path("LICENSE").is_file()
assert not Path("openspec/changes/close-demo-readiness").exists()
print("范围与发布声明检查通过")
PY
```

Expected: `范围与发布声明检查通过`。

- [ ] **Step 4: 请求代码审查但不执行外部动作**

Invoke `superpowers:requesting-code-review` against `master...HEAD`. Review must focus on:

- clean clone portability；
- package aliases and LICENSE；
- CI command correctness；
- document/spec factual consistency；
- accidental P2 scope creep。

Apply only confirmed P0/P1 findings, rerun the exact affected command, and commit fixes in Chinese. Do not create PR or push.

- [ ] **Step 5: 再次运行受修复影响的门禁并报告**

If Step 4 changed files, rerun Step 1 in full. Final report must state:

- exact pass counts and coverage from fresh output；
- real LLM E2E was not rerun unless it actually was；
- GitHub Actions was configured locally but not observed remotely because no push occurred；
- no tag、Release、PR or push was created；
- P2 was not implemented。

Do not claim completion if any required command is failing.
