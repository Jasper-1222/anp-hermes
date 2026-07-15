# ANP Hermes OpenSpec 开发路线图

日期：2026-07-08  
状态：初始能力、Top 10、社区就绪审计、ANP client skill、发布打包和 ANP SDK 0.8.9 基线均已完成；技术 Demo P0/P1 收口已完成。
参考分析：`docs/anp-hermes-current-implementation-analysis.md`

## 总体原则

本项目目标是为 ANP 社区贡献一个高质量 Hermes 接入参考实现。开发流程继续采用 OpenSpec：先定义 change 的 `proposal.md`、`design.md`、`tasks.md` 与 spec delta，经校验后再实现。

已完成路线遵循：

```text
先校准规格 → 再修 P0 正确性 → 再补 ANP 互通 → 再做工程化重构 → 最后做能力扩展
```

当前重点从”补功能”切换为”社区贡献前收尾”：文档事实一致、验证矩阵稳定、Demo 可保留当前状态供社区体验。

## 已完成变更顺序

1. `reconcile-anp-spec-docs` ✓
2. `protect-anp-runtime-secrets` ✓
3. `return-authentication-info` ✓
4. `harden-rpc-bridge` ✓
5. `support-anp-core-binding` ✓
6. `expand-agent-discovery` ✓
7. `harden-test-harness` ✓
8. `package-anp-plugin` ✓
9. `productionize-did-resolver` ✓
10. `expose-hermes-tools` ✓

## 已完成内容摘要

### 1. `reconcile-anp-spec-docs`

性质：文档与 OpenSpec 清理，不做业务代码实现  
状态：已归档

完成：

- 清理 OpenSpec active/archive 状态。
- 将 RPC 正常响应统一为 `result.response`。
- 修正 DID 文档路径说明为 path DID：`/agent/e1_<fingerprint>/did.json`。
- 明确当前阶段不强制要求 `agent.json`。
- 明确 `AuthenticationError.cause` 不作为硬性需求。
- 补全主 specs 的 Purpose。
- 更新 README / CLAUDE 中过期 OpenSpec 状态说明。

### 2. `protect-anp-runtime-secrets`

性质：安全修复 + 小规模实现  
状态：已归档

完成：

- 将运行态 DID/PEM、临时文件、备份文件和缓存加入 `.gitignore`。
- 默认 `data_dir` 调整为 `~/.hermes/data/anp-agent/`。
- 保留 `ANP_DATA_DIR` > `extra.data_dir` > 默认目录的优先级。
- 增加默认目录、配置覆盖、环境变量覆盖、损坏备份和私钥权限测试。
- 更新文档说明运行态目录和迁移边界。

### 3. `return-authentication-info`

性质：协议正确性修复  
状态：已归档

完成：

- 新增结构化认证结果，携带 caller DID 与成功认证响应头。
- 成功 `/agent/rpc` 响应透传允许的 `Authentication-Info`。
- 保持认证失败 challenge 头和错误分类不变。
- 增加认证与 server 测试。
- 新增并同步 `anp-authentication-info` main spec。

### 4. `harden-rpc-bridge`

性质：并发正确性 + JSON-RPC 错误语义修复  
状态：已归档

完成：

- `/agent/rpc` 严格校验单个 JSON-RPC 2.0 请求对象。
- 拒绝 batch、notification、无效 `jsonrpc`、无效 `id`、无效 `method` 和无效 `params`。
- 引入服务端内部 request id，客户端 JSON-RPC id 只用于响应回显和 metadata。
- 超时、取消、handler 异常和 pending 容量耗尽返回 JSON-RPC error。
- 增加并发隔离和错误路径测试。

### 5. `support-anp-core-binding`

性质：协议兼容增强  
状态：已归档

完成：

- 支持 `anp.core.binding.v1` envelope。
- `chat` 支持 legacy `params.message` 与 Core Binding `params.body.message`。
- 新增 `anp.get_capabilities`。
- 对 unsupported profile/security profile/invalid envelope 返回结构化 ANP public error。
- 更新 OpenRPC 并增加 server 测试。

### 6. `expand-agent-discovery`

性质：ANP-07 / ANP-08 互通增强  
状态：已归档

完成：

- 扩展 Agent Description 基础字段。
- 保持现有 `RemoteAgent.discover()` 兼容。
- 新增 `GET /.well-known/agent-descriptions`。
- 返回单 agent JSON-LD CollectionPage，item 的 `@id` 指向 `/agent/ad.json`。
- 增加发现端点测试。

### 7. `harden-test-harness`

性质：测试体系增强  
状态：已归档

完成：

- 修正 coverage source/omit，只统计 `anp_agent` 包。
- Echo E2E 使用临时 HOME / HERMES_HOME 和 mock LLM，不依赖真实 `~/.hermes/config.yaml`。
- LLM E2E 在缺少 slow flag、provider 或 API key 时于 gateway 启动前 skip。
- 补齐协议边界、私钥损坏、invalid request 等回归测试。
- 增加测试覆盖审计记录。

### 8. `package-anp-plugin`

性质：插件包化与发布质量  
状态：已归档

完成：

- 将运行时代码迁移到 `plugins/anp-agent/anp_agent/` 包。
- 根 `__init__.py` 改为轻量 Hermes entrypoint。
- 移除 `sys.path.insert` 和通用顶层模块导入。
- 更新 `pyproject.toml`、测试导入、coverage source 和 release zip 结构。
- 增加包化边界测试。

### 9. `productionize-did-resolver`

性质：生产可靠性 / 上游协作准备  
状态：已归档

完成：

- `ANP_DID_RESOLVER_BASE_URL` 限制为 loopback 本地测试用途。
- 生产默认依赖 DID WBA HTTPS 解析。
- HTTPS override 保持 TLS 校验。
- DID resolve timeout 加上默认值和上限。
- resolver wrapper 幂等，多实例冲突 fail fast。
- resolver 网络错误、安全分类和无效 DID Document 分类完成测试覆盖。

### 10. `expose-hermes-tools`

性质：能力增强  
状态：已归档

完成：

- 新增 `anp-hermes-tool-exposure` main spec。
- 新增默认关闭的 `tool_rpc` 配置结构。
- 实现 allowlist、denylist、caller DID 授权、schema 参数校验、工具执行、超时/取消/结果过大错误映射与审计记录。
- 将允许暴露的 Hermes registry tool 映射为 `hermes.tool.<tool_name>` JSON-RPC method。
- 更新 OpenRPC、Agent Description、`anp.get_capabilities` 和 `/agent/rpc` 路由。
- 保持高风险工具默认拒绝，且 tool RPC 失败不附带成功认证 `Authentication-Info`。

## 已完成变更摘要

以下 18 个 OpenSpec 变更已完成、同步并归档：

```text
reconcile-anp-spec-docs
protect-anp-runtime-secrets
return-authentication-info
harden-rpc-bridge
support-anp-core-binding
expand-agent-discovery
harden-test-harness
package-anp-plugin
productionize-did-resolver
expose-hermes-tools
review-community-readiness
add-anp-client-skill
update-anp-sdk-dependency
close-demo-readiness
```

## 当前不实施范围

本项目当前以技术 Demo 为完成目标。生产部署、Bearer 后续请求、per-DID 限流、持久化审计、resolver 上游改造、跨机器 DID 托管、AP2 和 E2EE 保留为可选后续主题，不属于本轮完成条件。

## 上下文恢复说明

后续若上下文溢出或新会话继续，建议按以下顺序读取：

1. `docs/anp-hermes-openspec-execution-state.md`
2. `docs/anp-hermes-openspec-roadmap.md`
3. `docs/anp-hermes-current-implementation-analysis.md`
4. `CLAUDE.md`
