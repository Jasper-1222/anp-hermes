# ANP Hermes OpenSpec 开发路线图

日期：2026-07-07  
状态：已确认，作为后续 OpenSpec 规范化开发的长期路线图  
参考分析：`docs/anp-hermes-current-implementation-analysis.md`

## 总体原则

当前项目已经完成 Hermes ↔ ANP 的最小可运行链路。后续目标是将其打磨为可贡献给 ANP 社区的高质量参考实现。

开发流程采用 OpenSpec：先定义 change 的 `proposal.md`、`design.md`、`tasks.md` 与 spec delta，经校验和确认后再实现。

执行顺序遵循：

```text
先校准规格 → 再修 P0 正确性 → 再补 ANP 互通 → 再做工程化重构 → 最后做能力扩展
```

## 推荐变更顺序

1. `reconcile-anp-spec-docs`
2. `protect-anp-runtime-secrets`
3. `return-authentication-info`
4. `harden-rpc-bridge`
5. `support-anp-core-binding`
6. `expand-agent-discovery`
7. `harden-test-harness`
8. `package-anp-plugin`
9. `productionize-did-resolver`
10. `expose-hermes-tools`

---

## 1. `reconcile-anp-spec-docs`

优先级：P0  
性质：文档与 OpenSpec 清理，不做业务代码实现

### Why

当前 OpenSpec、README、CLAUDE 与实现存在不一致，会误导后续开发：

- DID 文档路径文档写成 `/.well-known/did.json`，实际实现是 path DID 路由。
- `anp-rpc-bridge` spec 写 `result` 是字符串，实际实现和 E2E 使用 `result.response`。
- spec 要求 `agent.json`，实现未体现。
- spec 要求 `AuthenticationError.cause`，实现没有。
- 已完成变更仍留在 active changes。
- 多个主 specs 的 `Purpose` 仍为 `TBD`。

### What

- 清理 OpenSpec active/archive 状态。
- 修正 README、CLAUDE、OpenSpec 中与当前实现冲突的描述。
- 补全 main specs 的 Purpose。
- 明确哪些是当前契约，哪些进入后续 change。

### Out of scope

- 不改认证逻辑。
- 不改 bridge。
- 不新增端点。
- 不移动或删除运行态密钥文件。

### 涉及 specs

- `anp-discovery`
- `anp-identity`
- `anp-rpc-bridge`
- `anp-auth-error-classification`
- `anp-platform-adapter`

### 任务清单

- [ ] 清理已归档但仍在 `openspec/changes/` 中的变更。
- [ ] 将 RPC 正常响应统一描述为 `result.response`。
- [ ] 修正 DID 文档路径说明为 path DID：`/agent/e1_xxx/did.json`。
- [ ] 明确 `agent.json` 是否仍是需求；若不是，移除硬性要求。
- [ ] 明确 `AuthenticationError.cause` 是必选还是可选；建议降级为可选。
- [ ] 补全所有主 specs 的 `Purpose`。
- [ ] 更新 README / CLAUDE 中过期的 OpenSpec 状态说明。

### 验证

由用户手动执行：

```bash
cd /home/peter/anp-hermes
openspec validate reconcile-anp-spec-docs --strict
openspec list
```

---

## 2. `protect-anp-runtime-secrets`

优先级：P0  
性质：安全修复 + 小规模实现

### Why

当前源码目录下出现运行态文件：

```text
plugins/anp-agent/did.json
plugins/anp-agent/private_key.pem
plugins/anp-agent/jwt_private_key.pem
plugins/anp-agent/jwt_public_key.pem
```

这些文件未被 `.gitignore` 明确忽略，存在误提交风险。

### What

- 将运行态密钥和 DID 文件加入 `.gitignore`。
- 调整默认 `data_dir`，避免默认写入源码目录。
- 更新文档说明推荐运行态目录。
- 增加测试覆盖默认 data dir 和私钥权限。

### Out of scope

- 不自动删除当前已有未跟踪密钥文件。
- 不做包化重构。
- 不改 DID resolver。

### 涉及 specs

- `anp-identity`
- `anp-platform-adapter`
- 可新增：`anp-runtime-security`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_config.py tests/test_identity.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 3. `return-authentication-info`

优先级：P0  
性质：协议正确性修复

### Why

ANP DID WBA 规范要求首次 HTTP Message Signature 认证成功后，服务端通过 `Authentication-Info` 返回 access token。当前实现丢弃 verifier 返回的 response headers，客户端无法缓存 Bearer token。

### What

- 将认证结果改为结构化结果：caller DID + response headers。
- `/agent/rpc` 成功响应附加 `Authentication-Info`。
- 增加 Bearer token 后续请求测试。

### Out of scope

- 不改认证失败错误码。
- 不做授权策略。
- 不做 resolver 重构。

### 涉及 specs

- `anp-rpc-bridge`
- `anp-auth-error-classification`
- 可新增：`anp-did-wba-authentication`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_auth.py tests/test_server.py tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 4. `harden-rpc-bridge`

优先级：P0  
性质：并发正确性 + JSON-RPC 错误语义修复

### Why

当前 RPC bridge 有三个关键问题：

1. 超时、取消、handler 异常被包装成成功 `result.response`。
2. pending future 只按 `rpc_id` 全局索引，不区分 caller DID。
3. 数字 JSON-RPC id 会导致 pending key 和 `chat_id` 字符串不匹配。

### What

- Bridge 错误改为结构化异常。
- 超时、取消、handler 异常返回 JSON-RPC `error`。
- pending key 不再使用客户端 `rpc_id` 作为全局唯一 key。
- 引入服务端内部 request id。
- 明确 JSON-RPC id 策略：建议只接受非空字符串 id。

### Out of scope

- 不实现 `anp.get_capabilities`。
- 不兼容 `params.meta/body`。
- 不扩展 Agent Description。

### 涉及 specs

- `anp-rpc-bridge`
- `anp-platform-adapter`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_bridge.py tests/test_adapter.py tests/test_server.py tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 5. `support-anp-core-binding`

优先级：P1  
性质：协议兼容增强

### Why

当前 JSON-RPC 只支持简单 `params.message`，但 ANP Core Binding 还要求更严格的 JSON-RPC 校验、`params.meta/body` 结构以及 `anp.get_capabilities`。

### What

- 严格校验 `jsonrpc == "2.0"`。
- 明确拒绝 batch / notification。
- 校验 `id`、`params`、`message`。
- 兼容 `params.body.message`。
- 新增 `anp.get_capabilities`。
- 更新 OpenRPC。

### Out of scope

- 不改 Agent Description。
- 不新增 well-known discovery。
- 不暴露 Hermes tools。

### 涉及 specs

- `anp-rpc-bridge`
- 可新增：`anp-core-binding`
- `anp-discovery`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_server.py tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 6. `expand-agent-discovery`

优先级：P1  
性质：ANP-07 / ANP-08 互通增强

### Why

当前 `/agent/ad.json` 足够让本地 `RemoteAgent.discover()` 工作，但字段偏最小；同时缺少 ANP-08 主动发现入口。

### What

- 扩展 Agent Description 字段。
- 保持现有 `RemoteAgent.discover()` 兼容。
- 新增 `GET /.well-known/agent-descriptions`。
- 返回单 agent 的 CollectionPage。

### Out of scope

- 不做 DTR / Portal / Mediator。
- 不做多 agent registry。
- 不改变 RPC bridge。

### 涉及 specs

- `anp-discovery`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_server.py tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 7. `harden-test-harness`

优先级：P1  
性质：测试体系增强

### Why

当前测试主流程不错，但仍存在：coverage source 可能不准确、mock E2E 依赖真实 `~/.hermes/config.yaml`、slow E2E skip 时机偏晚、真实 bridge 超时路径和 token 流程测试不足。

### What

- 修正 coverage source/omit。
- mock E2E 使用临时 HOME / 临时 Hermes config。
- 提前 slow E2E skip。
- 增加 P0/P1 协议路径测试。

### Out of scope

- 不新增业务功能。
- 不做插件包化。
- 不引入复杂 CI secret 管理。

### 涉及 specs

- `anp-e2e-echo-test`
- `anp-e2e-llm-test`
- `anp-rpc-bridge`
- `anp-identity`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/ -q
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
python -m pytest tests/e2e/test_echo.py -v --run-e2e
```

可选慢速：

```bash
python -m pytest tests/e2e/test_llm.py -v --run-e2e --run-slow-e2e
```

---

## 8. `package-anp-plugin`

优先级：P2  
性质：插件包化与发布质量

### Why

当前插件使用 `sys.path.insert(0, plugin_dir)`，并通过 `from config import ...` 等通用模块名导入，存在模块污染风险。

### What

- 将业务模块移动到唯一包名下，例如 `anp_agent/`。
- 改为相对导入。
- 更新 `pyproject.toml`。
- 更新测试导入。
- 确保 Hermes 插件入口仍可工作。
- 明确 release zip 结构。

### Out of scope

- 不改变 ANP 协议行为。
- 不做 resolver 重构。
- 不暴露 Hermes tools。

### 涉及 specs

- `anp-platform-adapter`
- `dialog-plugin-install`
- 可新增：`anp-plugin-packaging`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
python -m pip install -e ".[test,dev]"
ruff check .
black --check .
python -m pytest tests/ --cov=anp_agent --cov-fail-under=85 -q
```

---

## 9. `productionize-did-resolver`

优先级：P2  
性质：生产可靠性 / 上游协作

### Why

当前 DID resolver 通过 monkeypatch ANP SDK 全局函数实现 timeout/base URL override。测试可用，但生产环境存在多实例配置冲突和 SSL 边界风险。

### What

- 明确 `ANP_DID_RESOLVER_BASE_URL` 仅用于测试/开发。
- 限制关闭 SSL 的条件。
- 文档说明生产 DID 解析方式。
- 规划向 ANP SDK 上游贡献 resolver injection。

### Out of scope

- 不 fork ANP SDK。
- 不阻塞 P0 修复。
- 不重写 DID WBA 方法。

### 涉及 specs

- `anp-auth-error-classification`
- `anp-platform-adapter`
- 可新增：`anp-did-resolver`

### 验证

```bash
cd /home/peter/anp-hermes/plugins/anp-agent
ruff check .
black --check .
python -m pytest tests/test_auth.py tests/test_integration.py -v
python -m pytest tests/ --cov=. --cov-fail-under=85 -q
```

---

## 10. `expose-hermes-tools`

优先级：P2 / 后续功能  
性质：能力增强

### Why

当前插件只暴露 `chat`，作为最小链路合理。但作为社区参考实现，后续应考虑将 Hermes tools / skills 映射为 ANP OpenRPC methods。

### What

- 调研 Hermes tools/skills 注册表。
- 设计 allowlist。
- 动态生成 OpenRPC methods。
- 将 JSON-RPC method dispatch 到 Hermes tools。
- 增加权限、审计和错误映射。

### Out of scope

- 不在 P0/P1 阶段做。
- 不暴露高风险工具。
- 不实现 AP2 / E2EE。

### 涉及 specs

- 可新增：`anp-hermes-tool-exposure`
- `anp-discovery`
- `anp-rpc-bridge`
- `anp-platform-adapter`

---

## 文档清理 vs 代码实现边界

### 只做文档 / OpenSpec 清理

归入 `reconcile-anp-spec-docs`：

- DID 文档路径说明修正。
- RPC result shape 修正。
- OpenSpec active/archive 状态清理。
- specs Purpose 补全。
- `agent.json` 要求去留确认。
- `AuthenticationError.cause` 要求去留确认。
- README / CLAUDE 中过期说明修正。

### 必须进入代码实现

- 返回 `Authentication-Info`。
- 支持 Bearer token 后续请求。
- Bridge 超时返回 JSON-RPC error。
- pending future caller 隔离。
- JSON-RPC id 严格校验。
- `.gitignore` 和默认 `data_dir` 安全修复。
- `anp.get_capabilities`。
- `/.well-known/agent-descriptions`。
- Agent Description 字段扩展。
- `params.meta/body` 兼容。
- hermetic E2E。
- 插件包化。
- resolver monkeypatch 生产边界。

## 上下文恢复说明

后续若上下文溢出或新会话继续，建议按以下顺序读取：

1. `docs/anp-hermes-openspec-execution-state.md`
2. `docs/anp-hermes-openspec-roadmap.md`
3. 当前 active change 的 `proposal.md`、`design.md`、`tasks.md`、`specs/**/spec.md`
4. 当前 change 涉及的实现文件和测试文件
