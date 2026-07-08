## Context

`anp-agent` 当前通过 ANP Python SDK 的 `DidWbaVerifier` 验证调用方 DID WBA HTTP Message Signatures。SDK 0.8.x 的 Python verifier 尚未暴露 resolver injection 配置入口，因此插件在 `auth.py` 中 monkeypatch `anp.authentication.did_wba_verifier.resolve_did_wba_document`，以支持：

- `ANP_DID_RESOLVE_TIMEOUT`：为 SDK resolver 增加可控超时。
- `ANP_DID_RESOLVER_BASE_URL`：在本地测试/E2E 中把调用方 DID Document 解析到本地 `DIDDocumentServer`。

该实现让测试闭环可运行，但生产边界不够清晰：override 下当前无条件 `verify_ssl=False`，非 loopback URL 也会被接受；全局 monkeypatch 配置由后创建的 `ANPAuth` 实例覆盖；部分 resolver 异常可能落入内部错误分类；文档也容易让用户把本地 resolver override 当作生产部署方案。

ANP DID WBA 的生产默认解析应遵循 DID method：

```text
did:wba:{domain}
-> https://{domain}/.well-known/did.json

did:wba:{domain}:{path...}:e1_<fingerprint>
-> https://{domain}/{path...}/e1_<fingerprint>/did.json
```

`ANP_DID_RESOLVER_BASE_URL` 只应替换测试 resolver 的 base URL，不应重写 DID、跳过 DID Document `id` 检查或绕过 proof/binding 校验。

## Goals / Non-Goals

**Goals:**

- 明确生产默认 resolver：未配置 override 时继续使用 ANP SDK DID WBA resolver，保持 HTTPS/TLS 校验与 DID WBA proof/binding 校验。
- 将 `ANP_DID_RESOLVER_BASE_URL` 收窄为本地开发/E2E/测试床便利配置，仅允许 loopback base URL。
- 避免 override 下无条件关闭 TLS：HTTP loopback 允许无 TLS；HTTPS override 默认 `verify_ssl=True`。
- 收紧 `ANP_DID_RESOLVE_TIMEOUT` 的解析边界，避免零值、负值或异常大值影响运行。
- 让 resolver wrapper 对网络、超时、DID document 无效等异常返回既有安全 JSON-RPC 错误分类。
- 保持 monkeypatch 幂等，避免不同 override 配置在同一进程中静默覆盖。
- 更新测试与文档，使测试床配置和生产部署方式区分清楚。

**Non-Goals:**

- 不 fork ANP SDK。
- 不重写 DID WBA method 或 verifier。
- 不新增 DTR、Portal、Mediator、OpenClaw 等外部依赖。
- 不在本变更中实现 Bearer token 后续请求验收。
- 不在本变更中扩展 `did:web` caller 支持；当前服务端认证仍以 `did:wba` caller 为主。
- 不把 resolver base URL 暴露到 `anp.get_capabilities`；resolver 是内部安全配置，不是公开能力。

## Decisions

### Decision 1: 保留 SDK monkeypatch，但封装 resolver policy

在 SDK Python verifier 暂无 resolver injection 前，继续保留当前 monkeypatch 兼容层，但把策略集中到 `auth.py` 的内部 helper：

- 解析并校验 base URL。
- 推导 `verify_ssl`。
- 解析并限制 timeout。
- 构造 wrapper 配置。
- 判断 wrapper 是否已安装、是否可更新。

替代方案：直接改用通用 `resolve_did_document()` 替换所有 verifier resolver 行为。该方案会偏离 SDK verifier 默认路径，风险更大；本变更只在配置了 loopback override 时走通用 resolver。

### Decision 2: `ANP_DID_RESOLVER_BASE_URL` 只允许 loopback

允许的 override host：`localhost`、`127.0.0.0/8`、`::1` 等 loopback 地址。拒绝 `http://example.com`、`https://example.com` 等非 loopback override，并在 `ANPAuth` 初始化时 fail fast。

理由：该变量目前主要服务本地 DID document server、E2E fixture 和测试床。生产部署应让 DID WBA 默认 resolver 通过 DID domain 的 HTTPS path 解析 DID Document，不应依赖服务端私有 override。

替代方案：允许远端 HTTPS override 并强制 `verify_ssl=True`。这需要额外定义证书信任、resolver mirror 权威性和运维策略，超出本次生产边界收敛目标。

### Decision 3: HTTP loopback 无 TLS，HTTPS override 保持 TLS 校验

当 base URL 是 loopback `http://...` 时，允许无 TLS，满足本地测试。若使用 `https://localhost...`，传给 SDK 通用 resolver 的 `verify_ssl` 为 `True`，不再无条件关闭 TLS。

替代方案：新增 `ANP_DID_RESOLVER_VERIFY_SSL=0`。该选项更灵活，但也更容易被误用；本阶段不增加危险开关。

### Decision 4: Timeout 使用默认值与上限，而不是启动失败

`ANP_DID_RESOLVE_TIMEOUT` 的非法、零值或负值回退默认值；超过上限时限制到上限。这样不会因为测试环境中误填 timeout 导致 gateway 无法启动，同时避免异常大值拖垮认证请求。

### Decision 5: 多实例冲突以 base URL override 为主 fail fast

同一 Python 进程中，wrapper 是进程级能力。若已经存在一个非空 base URL override，再创建另一个不同的非空 override，认证器初始化应失败，而不是静默覆盖。相同 override 或默认配置保持幂等。

该策略避免破坏现有测试中默认配置与短 timeout 的局部覆盖，同时封住最危险的“两个不同 DID resolver base URL 在同一进程中互相覆盖”场景。

### Decision 6: Resolver 异常统一进入安全分类

- timeout / `aiohttp.ClientError` → `DidWbaVerifierError("Failed to resolve DID document: ...")` → `-32002 DID 文档无法解析`。
- DID document `id` mismatch、proof/binding/结构校验失败等 `ValueError` → `DidWbaVerifierError("Invalid DID document: ...")` → `-32004 DID 文档无效`。
- 未预期异常仍记录日志并对外返回 `-32006 认证服务内部错误`，不泄露 URL、堆栈或原始异常详情。

## Risks / Trade-offs

- **Risk: 仍依赖 SDK 全局 monkeypatch** → Mitigation: wrapper 保持幂等，冲突配置 fail fast，并在文档中说明这是 SDK resolver injection 前的兼容边界。
- **Risk: 拒绝非 loopback override 可能影响已有实验部署** → Mitigation: 文档给出生产建议：让 DID Document 通过 DID domain 的标准 HTTPS path 可解析；本地测试继续使用 loopback override。
- **Risk: timeout 回退而非启动失败可能隐藏配置错误** → Mitigation: 记录 warning，并通过测试覆盖非法值、零值、负值和过大值。
- **Risk: HTTPS localhost 自签名证书测试不再默认通过** → Mitigation: 推荐本地测试使用 HTTP loopback；HTTPS override 默认安全。

## Migration Plan

1. 先新增 RED 测试覆盖 resolver override 成功路径、非 loopback 拒绝、HTTPS `verify_ssl=True`、timeout 边界、多实例冲突和 resolver 异常分类。
2. 更新 `auth.py` 内部 resolver policy 与 wrapper。
3. 更新 README、插件 README、CLAUDE.md 和执行状态，明确生产/测试边界。
4. 运行 OpenSpec validate、目标测试、普通测试、coverage、ruff/black 与 Echo E2E。
5. 同步 main specs 并归档。

回滚策略：若生产环境遇到兼容问题，可临时移除 `ANP_DID_RESOLVER_BASE_URL`，让插件回到默认 ANP SDK DID WBA HTTPS resolver 路径。