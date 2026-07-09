# anp-client-skill Specification

## Purpose
TBD - created by archiving change add-anp-client-skill. Update Purpose after archive.
## Requirements
### Requirement: 自包含 ANP 客户端 skill
系统 SHALL 提供一个可独立安装的 `anp-client` skill，使个人智能体能够作为 ANP 调用方发现并调用服务智能体。该 skill 的发布目录 SHALL 包含 `SKILL.md`、运行脚本和依赖说明，且不得依赖仓库外相对软链接或本机绝对路径。

#### Scenario: skill 目录可独立复制
- **WHEN** 用户复制或安装 `clients/anp-client/` 目录
- **THEN** 该目录包含运行所需的 `SKILL.md`、脚本文件和依赖说明
- **AND** 运行脚本不需要导入安装包外的仓库源码路径文件

#### Scenario: 角色术语清晰
- **WHEN** 用户阅读 `SKILL.md` 或 README
- **THEN** 文档将安装 `anp-client` skill 的调用方称为个人智能体
- **AND** 文档将安装 Hermes `anp-agent` plugin 的被调用方称为服务智能体

### Requirement: 通用 skill 安装包边界
`anp-client` skill SHALL 定义平台无关的安装包边界，使同一 skill 内容可通过压缩包、skill 发布网站、URL 下载或 ClawHub 等来源分发。安装包根目录 SHALL 至少包含 `SKILL.md`、`README.md`、`requirements.txt` 和 `scripts/`，且 MUST NOT 包含运行态 DID、私钥、临时文件、软链接或仓库绝对路径依赖。

#### Scenario: 安装包内容清单
- **WHEN** 用户阅读 README 或发布检查清单
- **THEN** 文档说明安装包根目录包含 `SKILL.md`、`README.md`、`requirements.txt` 和 `scripts/`
- **AND** 文档说明 `tests/` 可留在源码仓库内，不要求进入最终用户安装包

#### Scenario: 安装包安全检查
- **WHEN** 执行发布前检查
- **THEN** 检查确认安装包内容不包含 `did.json`、`private_key.pem`、临时文件、备份文件或软链接
- **AND** 检查确认安装包脚本不包含当前仓库根目录或其他本机绝对路径依赖

### Requirement: 命令式客户端入口
`anp-client` skill SHALL 提供命令式 Python CLI，至少支持 `whoami`、`serve-did`、`discover` 和 `chat` 四个入口，作为跨宿主稳定验收标准。

#### Scenario: 查看个人智能体身份
- **WHEN** 用户运行 `python3 scripts/anp_client.py whoami`
- **THEN** CLI 输出个人智能体 DID、身份目录、DID 文档路径和私钥路径

#### Scenario: 启动 DID 文档服务
- **WHEN** 用户运行 `python3 scripts/anp_client.py serve-did`
- **THEN** CLI 启动本地 DID 文档服务并输出 DID 文档 URL
- **AND** CLI 输出服务智能体本地开发所需的 `ANP_DID_RESOLVER_BASE_URL` 提示

#### Scenario: 发现服务智能体
- **WHEN** 用户运行 `python3 scripts/anp_client.py discover --endpoint <url>`
- **THEN** CLI 读取服务智能体的 Agent Description 和 OpenRPC 接口文档
- **AND** 输出服务 DID、服务名称、RPC endpoint 和可用方法

#### Scenario: discover JSON 输出
- **WHEN** 用户运行 `python3 scripts/anp_client.py discover --endpoint <url> --json`
- **THEN** CLI 输出包含 `service_did`、`name`、`rpc_endpoint`、`interface_url` 和 `methods` 的 JSON 对象

#### Scenario: 调用 chat
- **WHEN** 用户运行 `python3 scripts/anp_client.py chat --endpoint <url> --message <text>`
- **THEN** CLI 向服务智能体发送 DID WBA 签名的 JSON-RPC `chat` 请求
- **AND** 输出服务智能体回复或结构化错误

### Requirement: 个人智能体 DID WBA 身份管理
`anp-client` skill SHALL 在需要个人智能体身份的命令首次运行时自动生成 caller DID WBA 身份，并在后续调用中复用该身份。默认身份目录 SHALL 为 `~/.anp-client/`，且可通过 `ANP_CLIENT_HOME` 覆盖。公开发现命令 `discover` MUST NOT 为只读发现流程创建身份文件。

#### Scenario: 需要身份的命令首次使用自动生成身份
- **WHEN** 身份目录不存在且用户运行 `whoami`、`serve-did` 或 `chat`
- **THEN** CLI 生成 DID WBA 文档和私钥
- **AND** 将 DID 文档写入身份目录中的 `did.json`
- **AND** 将私钥写入身份目录中的 `private_key.pem`
- **AND** 第一期 DID 文档不声明 E2EE `keyAgreement` 能力

#### Scenario: discover 不创建身份
- **WHEN** 身份目录不存在且用户运行 `discover`
- **THEN** CLI 执行公开发现流程
- **AND** 不在身份目录中创建 `did.json` 或 `private_key.pem`

#### Scenario: 后续使用复用身份
- **WHEN** 身份目录中存在有效的 `did.json` 和 `private_key.pem`
- **THEN** CLI 加载并复用已有 DID
- **AND** 不生成新的 DID

#### Scenario: 私钥权限
- **WHEN** CLI 写入或加载 `private_key.pem`
- **THEN** 私钥文件权限为 `0o600`

#### Scenario: 环境变量覆盖身份目录
- **WHEN** 用户设置 `ANP_CLIENT_HOME` 并运行 CLI
- **THEN** CLI 在该目录中读取或写入 `did.json` 和 `private_key.pem`

#### Scenario: 损坏身份文件
- **WHEN** 身份目录中 `did.json` 或 `private_key.pem` 缺失、损坏、无法解析或彼此不匹配
- **THEN** CLI 返回明确错误
- **AND** 不静默生成新的 DID 覆盖现有身份

### Requirement: 本地 DID 文档服务
`anp-client` skill SHALL 提供本地 DID 文档服务，用于本地开发和 E2E 中让服务智能体解析个人智能体 DID。该服务 MUST 默认仅监听 loopback 地址。

#### Scenario: loopback DID 文档服务
- **WHEN** 用户运行 `serve-did`
- **THEN** CLI 在 `127.0.0.1` 上启动 HTTP 服务
- **AND** 按个人智能体 DID path segments 暴露 `/agent/e1_<fingerprint>/did.json` 形式的 DID 文档 URL

#### Scenario: 拒绝非 loopback 监听
- **WHEN** 用户尝试让 `serve-did` 监听非 loopback 地址
- **THEN** CLI 拒绝启动并提示第一期仅支持 loopback DID 文档服务

#### Scenario: 本地开发边界说明
- **WHEN** 用户阅读 `serve-did` 文档或命令输出
- **THEN** 文档或输出说明 `serve-did` 仅用于本地开发、测试和 E2E
- **AND** 文档说明默认个人智能体 DID 为 `did:wba:localhost...`，同机服务智能体可通过 `ANP_DID_RESOLVER_BASE_URL` 解析
- **AND** 文档说明 HTTPS endpoint 虽然通过传输安全策略校验，但远程服务通常无法解析本机 localhost DID；生产或跨机器调用需要公开 DID 文档托管或后续显式 hostname 初始化能力

### Requirement: 服务智能体发现
`anp-client` skill SHALL 支持通过直接 endpoint 或 Agent Description URL 发现服务智能体，并校验目标是 ANP 服务智能体。`discover` SHALL 输出已声明方法列表；`chat` SHALL 在调用前校验服务智能体声明了 `chat` 方法。

#### Scenario: 通过 endpoint 发现
- **WHEN** 用户运行 `discover --endpoint http://127.0.0.1:8900`
- **THEN** CLI 读取 `http://127.0.0.1:8900/agent/ad.json`
- **AND** CLI 读取 `http://127.0.0.1:8900/agent/interface.json`

#### Scenario: 通过 Agent Description URL 发现
- **WHEN** 用户运行 `discover --ad-url http://127.0.0.1:8900/agent/ad.json`
- **THEN** CLI 读取该 Agent Description
- **AND** 从 Agent Description 中选择 OpenRPC interface URL
- **AND** 从 OpenRPC `servers[].url` 推导 RPC endpoint，缺失时回退到 `{endpoint}/agent/rpc`

#### Scenario: 校验 ANP Agent Description
- **WHEN** CLI 读取 Agent Description
- **THEN** 响应的 `protocolType` 必须为 `ANP`
- **AND** 响应必须包含服务 DID、RPC endpoint 和接口文档引用

#### Scenario: discover 输出方法列表
- **WHEN** CLI 读取 OpenRPC interface 文档
- **THEN** `discover` 输出该文档声明的 methods 列表
- **AND** 即使 methods 不包含 `chat`，`discover` 仍返回发现结果

#### Scenario: chat 校验 chat 方法
- **WHEN** 用户运行 `chat` 且服务智能体 OpenRPC methods 不包含 `chat`
- **THEN** CLI 返回明确错误并列出已发现方法

### Requirement: DID WBA 签名 chat 调用
`anp-client` skill SHALL 使用个人智能体 DID WBA 身份对 JSON-RPC `chat` 请求生成 HTTP Message Signature，并调用服务智能体 `/agent/rpc`。

#### Scenario: legacy chat 请求
- **WHEN** 用户运行 `chat --endpoint <url> --message "你好"`
- **THEN** CLI 构造单个 JSON-RPC 2.0 请求对象
- **AND** 请求 `method` 为 `chat`
- **AND** 请求 `params.message` 为用户提供的消息文本
- **AND** 请求 `id` 为非空字符串

#### Scenario: 请求签名
- **WHEN** CLI 发送 `chat` 请求
- **THEN** CLI 使用 `DIDWbaAuthHeader` 或等效 ANP SDK 能力对实际发送的 HTTP body 生成 DID WBA HTTP Signature 请求头
- **AND** 请求头包含服务端认证所需的签名信息

#### Scenario: 成功响应
- **WHEN** 服务智能体返回 JSON-RPC 成功响应且 `result.response` 为文本
- **THEN** CLI 输出该回复文本
- **AND** 在 `--json` 模式下输出包含 `response`、服务 DID、个人智能体 DID、HTTP 状态和 JSON-RPC id 的 JSON 对象

#### Scenario: JSON-RPC 错误响应
- **WHEN** 服务智能体返回 JSON-RPC `error`
- **THEN** CLI 输出错误 `code`、`message` 和可用的 `data`
- **AND** 不把错误包装成成功回复

#### Scenario: DID 文档无法解析提示
- **WHEN** 服务智能体返回表示 DID 文档无法解析的 `-32002` 错误
- **THEN** CLI 提示用户先运行 `serve-did`
- **AND** 提示本地服务智能体需要配置 `ANP_DID_RESOLVER_BASE_URL`

#### Scenario: 签名无效提示
- **WHEN** 服务智能体返回表示 DID WBA 签名无效的 `-32001` 错误
- **THEN** CLI 提示用户检查个人智能体 DID、私钥、签名 body 与服务端 DID 文档解析结果是否匹配

#### Scenario: 缺少认证提示
- **WHEN** 服务智能体返回表示缺少认证头的 `-32003` 错误
- **THEN** CLI 提示用户必须通过 `chat` 命令发送 DID WBA 签名请求，而不是裸 HTTP 请求

### Requirement: endpoint 安全策略
`anp-client` skill SHALL 默认只允许 loopback HTTP endpoint 和 HTTPS endpoint，MUST 拒绝非 loopback 明文 HTTP endpoint。

#### Scenario: 允许 loopback HTTP
- **WHEN** 用户提供 `http://127.0.0.1:<port>`、`http://localhost:<port>` 或 `http://[::1]:<port>`
- **THEN** CLI 允许 discovery 和 chat 请求继续执行

#### Scenario: 允许 HTTPS
- **WHEN** 用户提供 `https://<host>` endpoint 或 AD URL
- **THEN** CLI 允许 discovery 和 chat 请求继续执行

#### Scenario: 拒绝非 loopback HTTP
- **WHEN** 用户提供 `http://example.com` 或局域网 IP HTTP endpoint
- **THEN** CLI 拒绝请求
- **AND** 提示第一期只允许 loopback HTTP 或 HTTPS

### Requirement: 自然语言样例解析契约
`anp-client` skill SHALL 在 `SKILL.md` 中说明自然语言触发方式，并提供测试夹具验证固定自然语言样例可规范化为命令式参数。

#### Scenario: 中文 chat 样例
- **WHEN** 测试夹具包含 `通过 ANP 调用 http://127.0.0.1:8900 的服务智能体，问它“你好”`
- **THEN** 该样例的期望规范化结果为 `action=chat`、`endpoint=http://127.0.0.1:8900`、`message=你好`

#### Scenario: AD URL chat 样例
- **WHEN** 测试夹具包含通过 `/agent/ad.json` URL 发送消息的自然语言表达
- **THEN** 该样例的期望规范化结果包含 `action=chat`、`ad_url=<agent-description-url>` 和 `message=<text>`

#### Scenario: discover 样例
- **WHEN** 测试夹具包含发现服务智能体的自然语言表达
- **THEN** 该样例的期望规范化结果为 `action=discover` 且包含 endpoint 或 AD URL

### Requirement: 一期能力边界
`anp-client` skill MUST NOT 在第一期调用 `hermes.tool.*`，不得执行远端工具，不得保存服务通讯录，也不得实现 AP2、E2EE、群聊或多轮 session 同步。

#### Scenario: 不调用工具 RPC
- **WHEN** 服务智能体 OpenRPC 文档声明 `hermes.tool.*` 方法
- **THEN** `anp-client` skill 不将这些方法作为第一期可调用能力暴露
- **AND** `chat` 流程不会调用任何 `hermes.tool.*` 方法

#### Scenario: 不保存通讯录
- **WHEN** 用户通过 URL 调用服务智能体
- **THEN** CLI 不把该服务写入持久化服务通讯录

### Requirement: 客户端 skill 测试覆盖
`anp-client` skill SHALL 提供单元、集成和端到端测试覆盖，验证身份管理、发现、签名 chat、安全边界和自然语言样例契约。

#### Scenario: 单元测试覆盖
- **WHEN** 运行客户端 skill 单元测试
- **THEN** 测试覆盖 DID 身份生成与复用、私钥权限、损坏身份错误、URL 安全策略、discovery 解析、chat payload 构造和自然语言样例夹具

#### Scenario: 集成测试覆盖
- **WHEN** 运行客户端 skill 集成测试
- **THEN** 测试使用本地 mock ANP 服务验证 `discover --json` 和 `chat --json`
- **AND** 测试确认 `chat` 请求携带 DID WBA 签名头

#### Scenario: E2E 覆盖
- **WHEN** 运行客户端 skill E2E 测试
- **THEN** 测试使用真实 Hermes `anp-agent` 服务智能体验证 `discover` 能发现 `chat`
- **AND** `chat --json` 返回包含 `response` 的成功结果
