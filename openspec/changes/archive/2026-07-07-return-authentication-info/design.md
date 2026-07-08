## Context

ANP DID WBA 规范要求服务端在首次 HTTP Message Signatures 认证成功后，通过 `Authentication-Info` 响应头返回 access token。当前插件在 `ANPAuth` 中创建 `DidWbaVerifierConfig` 时已经设置 `emit_authentication_info_header=True`，本地 ANP SDK 的 `verify_request()` 会在返回结果中提供 `response_headers`，但当前 `ANPAuth.authenticate()` 只返回 caller DID 字符串，`server.py` 因此无法把成功认证响应头转发给调用方。

认证失败路径已经有结构化 `AuthenticationError.headers` 和 challenge 头白名单转发，本变更只补齐成功认证路径，不改变失败响应契约。

## Goals / Non-Goals

**Goals:**

- 在 DID WBA 认证成功后，将 verifier 产生的 `Authentication-Info` 响应头随 `/agent/rpc` 成功响应返回。
- 将认证成功结果从字符串扩展为结构化对象，包含 caller DID 与可转发响应头。
- 只转发明确允许的成功认证响应头，防止任意 verifier 头透传。
- 保持 JSON-RPC body 不变：成功响应仍为 `result.response`。
- 增加单元测试覆盖认证结果结构与 server 成功响应头。

**Non-Goals:**

- 不实现 Bearer token 后续请求验收逻辑；本变更只返回首次认证后的 `Authentication-Info`。
- 不改变认证失败错误码、challenge 头转发或安全响应约束。
- 不改变 DID 文档解析、签名验证算法、JWT 过期时间或密钥管理策略。
- 不在 HTTP 明文测试环境外新增 HTTPS 强制策略；该安全策略可由后续生产化变更处理。

## Decisions

### 决策 1：新增认证成功结果对象

新增一个轻量结构，例如 `AuthenticationResult`，包含：

- `caller_did: str`
- `headers: dict[str, str]`

`ANPAuth.authenticate()` 返回该结构，而不是单独返回 DID 字符串。

理由：

- 避免让 `server.py` 直接依赖 ANP SDK verifier 的原始 result shape。
- 后续如果需要携带认证 scheme、token 元信息或审计字段，可以在认证模块内部扩展，不污染 server 逻辑。
- 比返回 tuple 更可读，降低字段顺序错误风险。

备选方案：

- 返回 `(caller_did, headers)` tuple：改动较少，但可读性弱。
- 继续返回字符串并在 server 中调用 verifier：破坏认证职责封装，不采用。

### 决策 2：成功响应头使用白名单过滤

`ANPAuth` 从 verifier result 的 `response_headers` 中只提取：

```text
Authentication-Info
```

提取时按 HTTP header 名大小写不敏感匹配，并以 canonical `Authentication-Info` 名称输出；不转发 `Authorization` 或任意其他头。

理由：

- ANP 规范明确要求通过 `Authentication-Info` 返回 access token，而不是响应 `Authorization` 头。
- 现有失败路径也采用白名单转发 challenge 头，成功路径应保持同样的安全边界。
- 避免 SDK 或测试 mock 中意外返回的内部头被暴露。

### 决策 3：server 在所有成功 JSON-RPC 业务响应中附带认证成功头

`server.py` 在认证通过后保存认证结果，并在 `chat` 成功响应中传入 `headers=auth_result.headers or None`。

方法不存在、bridge 异常等非认证成功业务错误不附带 `Authentication-Info`，因为这些响应不代表一次完整业务调用成功。

### 决策 4：测试保持单元级覆盖

新增/调整测试：

- `test_auth.py` 验证 `authenticate()` 返回 caller DID 与过滤后的 `Authentication-Info`。
- `test_server.py` 验证 `/agent/rpc` 成功响应携带 `Authentication-Info`。
- `test_server.py` 验证认证结果无 headers 时成功响应不出现空 `Authentication-Info`。
- 保留失败 challenge 头测试，确认失败路径不回归。

## Risks / Trade-offs

- [Risk] 调整 `authenticate()` 返回类型会影响所有调用点。  
  → Mitigation：当前调用点集中在 `server.py` 和测试中；任务中显式搜索并更新所有调用点。

- [Risk] SDK 结果中 `response_headers` 可能为空或缺失。  
  → Mitigation：认证模块默认返回空 dict；server 仅在非空时传入响应头。

- [Risk] 转发过多头可能泄露内部实现。  
  → Mitigation：只允许 `Authentication-Info`，不转发响应 `Authorization` 或自定义内部头。

## Migration Plan

1. 新增认证成功结果结构与 `Authentication-Info` 白名单提取逻辑。
2. 更新 `server.py` 使用 `auth_result.caller_did` 调用 bridge，并在成功响应中附带 `auth_result.headers`。
3. 更新现有测试 mock，让 `mock_auth.authenticate` 返回新的结构。
4. 增加成功响应头测试并运行认证/server 测试。
5. 更新文档与执行状态。

## Open Questions

无。