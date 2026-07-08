# anp-did-resolver Specification

## Purpose

定义 `anp-agent` 对调用方 DID WBA 文档解析的生产默认行为、本地测试 resolver override、TLS/timeout 边界、ANP SDK monkeypatch 兼容约束与安全错误分类。

## Requirements

### Requirement: DID WBA 默认生产解析
`anp-agent` SHALL 默认使用 ANP Python SDK 的 DID WBA resolver 按 DID method 规则解析调用方 DID Document；未配置 resolver override 时，解析 SHALL 使用 DID 中的 domain/path、HTTPS 与 SDK 默认的 DID Document `id`、proof、binding 校验。

#### Scenario: 解析 path DID
- **WHEN** 调用方 DID 为 `did:wba:example.com:agent:e1_<fingerprint>` 且未配置 `ANP_DID_RESOLVER_BASE_URL`
- **THEN** resolver SHALL 按 DID WBA 规则解析到 `https://example.com/agent/e1_<fingerprint>/did.json`
- **AND** verifier SHALL 校验返回 DID Document 的 `id`、proof 与 binding

#### Scenario: 不使用测试 override
- **WHEN** 未设置 `ANP_DID_RESOLVER_BASE_URL`
- **THEN** `anp-agent` SHALL NOT 改写 DID domain 或关闭 SDK 默认 TLS 校验

### Requirement: 本地测试 resolver override
`ANP_DID_RESOLVER_BASE_URL` SHALL 仅作为本地开发、测试床与 E2E 测试便利配置。该变量 SHALL 只接受 loopback base URL，并且 SHALL 只替换 resolver 的 base URL，不改变 DID path 到 HTTP path 的映射，也不得跳过 DID Document `id`、proof 或 binding 校验。

#### Scenario: loopback HTTP override 可用
- **WHEN** `ANP_DID_RESOLVER_BASE_URL` 设置为 `http://127.0.0.1:<port>` 或 `http://localhost:<port>`
- **THEN** resolver SHALL 使用该 loopback base URL 获取 DID Document
- **AND** 仍 SHALL 按 DID path 追加 `/<path...>/did.json`
- **AND** 仍 SHALL 校验 DID Document 与原 DID 匹配

#### Scenario: 非 loopback override 被拒绝
- **WHEN** `ANP_DID_RESOLVER_BASE_URL` 设置为 `http://example.com` 或 `https://example.com`
- **THEN** `ANPAuth` 初始化 SHALL fail fast
- **AND** 不得静默回退或静默覆盖为该非 loopback resolver

### Requirement: Resolver TLS 边界
`anp-agent` SHALL NOT 对非本地 resolver 关闭 TLS 校验。loopback `http://` override MAY 用于本地测试；`https://` override SHALL 使用 TLS 校验。

#### Scenario: loopback HTTP 允许无 TLS
- **WHEN** resolver override 为 loopback `http://` URL
- **THEN** resolver MAY 使用无 TLS 的本地 HTTP 连接

#### Scenario: HTTPS override 保持 TLS 校验
- **WHEN** resolver override 为 loopback `https://` URL
- **THEN** resolver SHALL 调用 SDK 通用 resolver 时启用 `verify_ssl=True`

### Requirement: Resolver timeout 配置
`ANP_DID_RESOLVE_TIMEOUT` SHALL 控制 DID Document 解析超时。非法、零值或负值 SHALL 回退默认值；超过上限的值 SHALL 被限制到上限；解析超时 SHALL 对外映射为 `-32002 DID 文档无法解析`。

#### Scenario: 非法 timeout 回退默认值
- **WHEN** `ANP_DID_RESOLVE_TIMEOUT` 不是数字、为零或为负数
- **THEN** `anp-agent` SHALL 使用默认 resolver timeout

#### Scenario: 超大 timeout 被限制
- **WHEN** `ANP_DID_RESOLVE_TIMEOUT` 大于允许上限
- **THEN** `anp-agent` SHALL 使用上限值而不是原始超大值

#### Scenario: resolver 超时分类
- **WHEN** DID Document 解析超过有效 timeout
- **THEN** `/agent/rpc` 认证失败 SHALL 返回 JSON-RPC `error.code=-32002` 与消息 `DID 文档无法解析`

### Requirement: Monkeypatch 兼容边界
在 ANP Python SDK 暂未提供 resolver injection 前，`anp-agent` MAY 使用进程级 monkeypatch 包装 SDK resolver；该 wrapper SHALL 幂等，且不同非空 resolver base URL 配置不得在同一进程内静默覆盖。

#### Scenario: 相同配置幂等
- **WHEN** 同一进程内多次创建相同 resolver 配置的 `ANPAuth`
- **THEN** resolver wrapper SHALL 不重复嵌套
- **AND** 创建过程 SHALL 成功

#### Scenario: 不同 override 配置冲突
- **WHEN** 同一进程内已安装 `ANP_DID_RESOLVER_BASE_URL=A` 的 resolver wrapper
- **AND** 后续尝试创建 `ANP_DID_RESOLVER_BASE_URL=B` 且 `A != B`
- **THEN** `ANPAuth` 初始化 SHALL fail fast
- **AND** 不得静默覆盖进程级 resolver 配置

### Requirement: Resolver 错误安全分类
Resolver wrapper SHALL 将网络、超时、HTTP 获取失败、DID Document 无效和未预期异常映射到既有安全认证错误分类，不得向调用方泄露内部 URL、原始网络异常消息、堆栈或密钥信息。

#### Scenario: 网络错误分类为无法解析
- **WHEN** resolver 触发 `aiohttp.ClientError`
- **THEN** 认证失败 SHALL 映射为 `-32002 DID 文档无法解析`

#### Scenario: DID Document 无效分类为无效文档
- **WHEN** resolver 已获取 DID Document 但 `id`、proof 或 binding 校验失败
- **THEN** 认证失败 SHALL 映射为 `-32004 DID 文档无效`

#### Scenario: 内部细节不外泄
- **WHEN** resolver 失败被返回给 `/agent/rpc` 调用方
- **THEN** 响应 SHALL 只包含规范错误码与对外消息
- **AND** 不得包含 resolver base URL、原始异常详情或堆栈
