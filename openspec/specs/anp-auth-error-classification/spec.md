# anp-auth-error-classification Specification

## Purpose

定义 `anp-agent` 插件在 DID WBA 认证失败时的错误分类与 JSON-RPC/HTTP 响应契约，使调用方能够根据错误码自助定位问题。

## Requirements

### Requirement: 错误码定义
认证失败 SHALL 映射到 6 个具体的 JSON-RPC 错误码，每个错误码对应固定的 HTTP 状态码与对外消息。

#### Scenario: 错误码表格
- **WHEN** 认证失败并被分类为其中一种场景
- **THEN** 返回对应的 `error.code`、`HTTP status` 与 `error.message`：
  | code | HTTP status | 消息 |
  | --- | --- | --- |
  | `-32001` | 401 | DID WBA 签名无效 |
  | `-32002` | 401 | DID 文档无法解析 |
  | `-32003` | 401 | 缺少认证头 |
  | `-32004` | 401 | DID 文档无效 |
  | `-32005` | 403 | 认证方法未授权 |
  | `-32006` | 500 | 认证服务内部错误 |

### Requirement: AuthenticationError 结构
`AuthenticationError` SHALL 携带 `status_code`、`rpc_code`、`message` 与 `headers`，供调用方无需重新解析字符串即可构造响应。

#### Scenario: 构造结构化异常
- **WHEN** 认证器检测到具体失败原因
- **THEN** 抛出包含正确 `status_code`、`rpc_code`、`message` 与可选 `headers` 的 `AuthenticationError`

### Requirement: 基于 verifier 错误消息的分类
对于 `DidWbaVerifierError`，认证器 SHALL 根据 `exc.message` 与 `exc.status_code` 判断具体分类，而非仅依赖异常类型或子串匹配。

#### Scenario: DID 文档解析超时
- **WHEN** verifier 抛出包含 `timeout` 的 `DidWbaVerifierError`
- **THEN** 分类为 `-32002 DID 文档无法解析`

#### Scenario: 签名验证失败
- **WHEN** verifier 返回签名相关错误且未涉及 DID 文档解析
- **THEN** 分类为 `-32001 DID WBA 签名无效`

#### Scenario: 缺少认证头
- **WHEN** verifier 返回缺少 `Signature` / `Signature-Input` / `Authorization` 的错误
- **THEN** 分类为 `-32003 缺少认证头`

#### Scenario: DID 文档无效
- **WHEN** verifier 返回 DID 文档 proof 或 binding 校验失败
- **THEN** 分类为 `-32004 DID 文档无效`

#### Scenario: 认证方法未授权
- **WHEN** verifier 返回 verification method 未列入 `authentication` 的错误
- **THEN** 分类为 `-32005 认证方法未授权`

### Requirement: Resolver 网络错误包装
`ANPAuth` 的 resolver wrapper SHALL 将 `aiohttp.ClientError` 与 `asyncio.TimeoutError` 统一包装为 `DidWbaVerifierError("Failed to resolve DID document: ...", status_code=401)`，确保其被分类为 DID 文档解析失败。resolver wrapper SHALL 将 DID Document `id` mismatch、proof、binding 或结构校验失败包装为 `DidWbaVerifierError("Invalid DID document: ...", status_code=401)`，确保其被分类为 DID 文档无效。resolver policy/config 错误 SHALL 在初始化时 fail fast 或映射为安全内部错误，不得向远端调用方泄露内部配置。

#### Scenario: 错误的 resolver base URL
- **WHEN** `ANP_DID_RESOLVER_BASE_URL` 指向不可达 loopback 地址并触发 `aiohttp.ClientError`
- **THEN** 认证器抛出 `-32002 DID 文档无法解析`，而非 `-32001 DID WBA 签名无效`

#### Scenario: DID Document binding 校验失败
- **WHEN** resolver 获取到 DID Document 但 SDK 校验返回 proof 或 binding 失败
- **THEN** 认证器抛出 `-32004 DID 文档无效`，而非 `-32006 认证服务内部错误`

#### Scenario: resolver policy 初始化失败不外泄
- **WHEN** resolver override 配置违反本地测试策略并在 `ANPAuth` 初始化时失败
- **THEN** 错误信息 SHALL 面向本地运维诊断
- **AND** 不得通过 `/agent/rpc` 响应向远端调用方泄露内部配置值

### Requirement: 安全响应约束
对外响应 SHALL 仅暴露规范定义的错误码与消息；内部 URL、原始网络异常消息、堆栈或 JWT 密钥信息不得泄露给调用方。

#### Scenario: 内部异常不外泄
- **WHEN** 认证器内部出现未预期异常
- **THEN** 记录日志后对外返回 `-32006 认证服务内部错误`，且不包含堆栈信息

### Requirement: Challenge 头转发
当认证失败且 `DidWbaVerifierError` 返回 HTTP 401 响应头时，适配器 SHALL 将 `WWW-Authenticate` 和 `Accept-Signature` 头转发给调用方。

#### Scenario: 转发 challenge 头
- **WHEN** verifier 响应包含 `WWW-Authenticate` 或 `Accept-Signature` 头
- **THEN** 这些头出现在 HTTP 401 响应中
