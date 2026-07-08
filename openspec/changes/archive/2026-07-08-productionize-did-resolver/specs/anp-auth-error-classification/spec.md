## MODIFIED Requirements

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