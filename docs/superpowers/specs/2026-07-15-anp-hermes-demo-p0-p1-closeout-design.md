# ANP Hermes 技术 Demo P0/P1 收口设计

日期：2026-07-15

## 背景

`anp-hermes` 已完成第一期 ANP × Hermes 技术验证链路：Hermes 服务端插件、DID WBA 身份认证、发现与 OpenRPC、JSON-RPC 桥接、默认关闭的 Hermes tool RPC、ANP 调用端 skill、本地 E2E 和双发布包构建均已落地。

当前剩余问题主要是仓库收口，而非继续扩展协议或生产能力：社区 README 尚未提交，CI 监听错误的默认分支，少量格式与测试隔离门禁未收口，仓库缺少实际 MIT 许可证文件，发布资产名称不统一，进展文档和两个主规格落后于实际状态。

本项目定位为技术 Demo。本轮只完成 P0/P1 中影响可公开、可验证和事实一致性的工作，不追求生产系统标准，也不实施 P2。

## 目标

完成一个最低充分的技术 Demo 仓库收口，使其满足：

1. 社区 README 被安全保全并集成；
2. 干净 clone 可以运行确定性测试并构建发布包；
3. GitHub Actions 在默认分支 `master` 上实际触发；
4. 当前 Ruff、Black 和测试端口隔离问题被修正；
5. 仓库和发布包包含 MIT `LICENSE`；
6. 发布资产同时具备版本化名称和稳定别名；
7. README、插件 README、CLAUDE.md、状态文档和主规格反映同一当前事实；
8. 所有工作由一个轻量 OpenSpec change 记录、同步并归档。

## 非目标

本轮明确不包含：

- Git tag、GitHub Release 或公开发布；
- Release workflow、checksum、签名、SBOM；
- systemd、Docker、反向代理或生产部署指南；
- Bearer token 后续请求扩展；
- per-DID 限流、工具并发治理或持久化审计；
- ANP SDK resolver injection 上游改造；
- 跨机器 caller DID 托管；
- AP2、E2EE、群聊、多轮 session 等 P2 能力；
- 无关重构、覆盖率提升或生产级质量流程。

## 分支与集成策略

采用“README 先保全、统一分支再收口”的流程：

```text
README worktree
  └─ 提交 README + 原 README 设计/计划
             │
             │ git merge
             ▼
chore/close-demo-readiness
  ├─ OpenSpec: close-demo-readiness
  ├─ CI / 格式 / 测试隔离
  ├─ LICENSE / 发布资产别名
  ├─ 状态文档 / CLAUDE.md / 主规格
  └─ 完整本地验证
```

具体约束：

- 现有 README worktree 中的未提交 README 必须先进入 Git 提交，避免删除 worktree 时丢失；
- 现有两份 README 设计与计划文档全部保留并提交；
- 分支之间只使用 `git merge` 或 `git cherry-pick` 集成，禁止手工复制覆盖；
- 最终保留统一收口分支供审阅，不推送、不建 PR、不创建 Release，除非用户之后另行要求；
- `.claude/worktrees/` 不加入 Git。

## OpenSpec 组织

创建单一 `close-demo-readiness` change，不为每个小修复拆分独立变更。该 change 覆盖三个主题：

1. **Demo 仓库验证门禁**：默认分支 CI、确定性测试、格式检查和干净 clone 可验证；
2. **Demo 发布包边界**：MIT LICENSE、版本化资产、稳定别名和 zip 内容；
3. **Demo 状态一致性**：README、CLAUDE.md、三份进展文档和主规格同步。

实现完成后：

1. 验证 change 和代码；
2. 将 delta specs 同步到 main specs；
3. 归档 `close-demo-readiness`；
4. 确认 `openspec list --json` 恢复为空。

## CI 与最低质量门禁

CI 只使用 Python 3.12。技术 Demo 不维护 Python 3.10/3.11/3.12 三版本矩阵。

单一 CI job 顺序执行：

1. checkout；
2. 安装插件 `.[test,dev]` 与客户端开发依赖；
3. 准备 OpenSpec CLI；
4. `openspec validate --all`；
5. 根级依赖/发布测试；
6. 客户端 pytest、Ruff 和 Black；
7. 构建版本化 zip 与稳定别名；
8. 插件 Ruff 和 Black；
9. 插件普通测试；
10. 插件覆盖率门禁 `>=85%`。

CI 监听：

- `push` 到 `master` 和 `feature/*`；
- 以 `master` 为目标分支的 pull request。

真实 LLM E2E 不进入 CI。CI 只运行无凭据、确定性的检查。

本轮只修复已知门禁问题：

- Black 格式化 `plugins/anp-agent/tests/e2e/conftest.py`；
- 清理 `scripts/verify_anp_sdk.py` 的未使用导入；
- adapter 连接测试显式使用动态端口，避免和本机或 CI 上的固定端口冲突；
- 包化测试不再要求仓库预先存在 ignored `anp-agent.zip`。

不提高覆盖率阈值，不重构无关代码。

## 发布包与许可证

### 资产名称

一次运行 `scripts/package_anp_release.py` 生成：

```text
dist/
├── anp-agent-plugin-0.1.0.zip
├── anp-agent.zip
├── anp-client-skill-0.1.0.zip
└── anp-client.zip
```

版本化名称用于追踪具体版本；稳定别名用于 README 中的固定下载约定。稳定别名由脚本直接生成，不依赖手工复制。

### 干净 clone 测试

插件包化测试调用打包 API 或使用临时目录中的产物进行验证，不要求 `plugins/anp-agent/anp-agent.zip` 在测试前已经存在。这样普通测试可在干净 clone 中直接运行。

### LICENSE

- 仓库根新增标准 MIT `LICENSE`；
- plugin 和 client 两个发布包都包含 `LICENSE`；
- 根 README 的 MIT 声明链接到该文件；
- `plugins/anp-agent/pyproject.toml` 保持现有 MIT 元数据，不增加额外发布元数据。

### Release 表述

本轮不创建 GitHub Release，因此文档不得声称仓库当前已有可下载 Release。插件 README 可以描述“发布 Release 后”的稳定 URL 约定，其中插件资产为 `anp-agent.zip`，客户端资产为 `anp-client.zip`。

## 文档与规格同步

### 根 README

保留已批准的 ANP × Hermes 技术验证 Demo 定位，包含：

- 项目目的、问题和交互链路；
- Hermes 服务端插件与 ANP 调用端 skill；
- 快速体验、测试、打包和社区参与；
- tool RPC 默认关闭和当前审计 callback 边界；
- 不宣称已有 GitHub Release；
- MIT LICENSE 链接。

### 插件 README

只做与 P0/P1 直接相关的事实更新：

- 下载资产使用稳定别名；
- 明确 Release 尚需另行创建，或用条件式表述；
- 测试命令不再要求手工准备 ignored zip；
- 不扩展生产部署说明。

### 三份进展文档

更新：

- `docs/anp-hermes-openspec-execution-state.md`
- `docs/anp-hermes-openspec-roadmap.md`
- `docs/anp-hermes-current-implementation-analysis.md`

共同要求：

- 记录此前 17 个变更均已归档；
- 本轮执行时 active change 为 `close-demo-readiness`，归档后 active 恢复为空；
- 补充客户端 skill、双包打包和 ANP SDK 0.8.9；
- 当前阶段改为技术 Demo 仓库收口；
- 修正默认审计 sink 的描述；
- 删除“先完成 review-community-readiness”的过期建议；
- P2 仅列为当前不实施的可选后续边界，不编写实施计划。

### CLAUDE.md

更新：

- 归档变更总数和当前状态；
- 仓库结构加入 `clients/anp-client/` 与发布脚本；
- 常用验证命令覆盖根级、客户端和插件；
- 明确当前项目定位为技术 Demo，不以生产化为本轮目标；
- 保留现有安全硬约束。

### 主规格

- `openspec/specs/anp-client-skill/spec.md`：用正式中文 Purpose 替换归档占位文本；
- `openspec/specs/anp-community-readiness/spec.md`：记录社区审计、客户端、发布包和 SDK 基线已完成，更新最低验证矩阵，移除“先完成已归档变更”的建议。

只更新事实和验收约束，不新增 P2 功能需求。

## 验证设计

必须运行并通过：

```text
openspec validate --all
python3 -m pytest tests/ -q
python3 -m pytest clients/anp-client/tests/ -q
ruff check <根级脚本、客户端、插件>
black --check <根级脚本、客户端、插件>
python3 scripts/package_anp_release.py --dist-dir <临时目录>
cd plugins/anp-agent
python3 -m pytest tests/ -q
python3 -m pytest --cov=anp_agent --cov-fail-under=85 -q
python3 -m pytest tests/e2e/ -q --run-e2e
git diff --check
```

说明：

- 真实 LLM E2E 不作为本轮门禁，只保留已有历史验证说明；
- 临时发布目录在验证后清理；
- 测试不依赖固定 8900 端口或预先存在的 ignored zip；
- 不通过跳过、忽略退出码或降低阈值换取绿灯。

## 完成定义

本轮完成时必须满足：

1. README worktree 的成果已经提交并通过 Git 合入统一收口分支；
2. 新用户从干净 clone 能安装依赖、运行确定性测试并构建四个发布资产；
3. CI 能在 `master` push/PR 上触发；
4. 当前本地 Ruff、Black、pytest、coverage、E2E 和 OpenSpec 门禁通过；
5. 仓库与两个 zip 包含 MIT `LICENSE`；
6. README、插件 README、CLAUDE.md、三份状态文档和主规格事实一致；
7. `close-demo-readiness` 已同步并归档，active changes 为空；
8. 没有 P2 或生产级能力进入变更；
9. 未创建 tag、GitHub Release、PR 或远端推送。
