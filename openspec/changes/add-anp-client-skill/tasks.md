## 1. Skill 结构与文档

- [ ] 1.1 创建 `clients/anp-client/` 自包含 skill 目录，包含 `SKILL.md`、`README.md`、`requirements.txt`、`scripts/` 和 `tests/`。
- [ ] 1.2 编写 `SKILL.md`，明确个人智能体/服务智能体术语、自然语言触发方式、命令式入口和一期能力边界。
- [ ] 1.3 编写 `README.md`，说明安装依赖、运行 `whoami`、`serve-did`、`discover`、`chat` 的最小流程，以及通用 skill 安装包内容清单。
- [ ] 1.4 编写 `requirements.txt` 声明自包含 skill 运行依赖，并编写 `requirements-dev.txt` 声明源码仓库测试、格式化与 lint 依赖。

## 2. DID 身份与 DID 文档服务

- [ ] 2.1 实现 `scripts/did_identity.py`，支持在 `~/.anp-client/` 或 `ANP_CLIENT_HOME` 中自动生成和加载 `did.json`、`private_key.pem`。
- [ ] 2.2 确保 `private_key.pem` 写入和加载后的权限为 `0o600`。
- [ ] 2.3 实现身份文件缺失、损坏、无法解析或私钥与 DID 文档不匹配时的明确错误，不静默覆盖已有身份。
- [ ] 2.4 实现 `scripts/did_server.py`，按 DID WBA path DID 暴露 `/agent/e1_<fingerprint>/did.json`。
- [ ] 2.5 确保 `serve-did` 默认只监听 `127.0.0.1`，并拒绝非 loopback 监听配置。
- [ ] 2.6 在 `serve-did` 输出中包含个人智能体 DID、DID 文档 URL 和服务智能体本地开发所需的 `ANP_DID_RESOLVER_BASE_URL` 提示。

## 3. CLI、发现与 chat 调用

- [ ] 3.1 实现 `scripts/signing.py`，复用 `DIDWbaAuthHeader` 对实际发送的 JSON-RPC body 生成 DID WBA HTTP Signature 请求头。
- [ ] 3.2 实现 `scripts/anp_client.py whoami`，输出个人智能体 DID 和身份文件路径。
- [ ] 3.3 实现 `scripts/anp_client.py serve-did`，启动本地 DID 文档服务。
- [ ] 3.4 实现 endpoint 与 AD URL 规范化逻辑，只允许 loopback HTTP 与 HTTPS。
- [ ] 3.5 实现 `discover --endpoint`，读取 `{endpoint}/agent/ad.json` 与 `{endpoint}/agent/interface.json`。
- [ ] 3.6 实现 `discover --ad-url`，从 Agent Description 推导 OpenRPC interface URL，并从 OpenRPC `servers[].url` 推导 RPC endpoint（缺失时回退 `/agent/rpc`）。
- [ ] 3.7 校验 Agent Description 的 `protocolType: "ANP"`、服务 DID、RPC endpoint 和 interface 引用。
- [ ] 3.8 确保 `discover` 输出 OpenRPC methods 列表但不要求包含 `chat`；`chat` 调用前校验 OpenRPC methods 包含 `chat`，否则列出已发现方法并返回明确错误。
- [ ] 3.9 实现 `chat`，使用 legacy `params.message` 构造单个 JSON-RPC 2.0 请求并签名调用 `/agent/rpc`。
- [ ] 3.10 实现默认人类可读输出与 `--json` 输出，成功时包含服务 DID、个人智能体 DID、HTTP 状态、JSON-RPC id 和 `response`。
- [ ] 3.11 映射常见 HTTP、JSON-RPC 和 DID WBA 认证错误为清晰提示，尤其覆盖 `-32001`、`-32002`、`-32003` 和缺少 `chat` 方法。

## 4. 自然语言样例契约

- [ ] 4.1 在 `SKILL.md` 中列出固定自然语言样例及其等价命令式参数。
- [ ] 4.2 增加自然语言样例夹具，覆盖中文 chat、AD URL chat 和 discover 表达。
- [ ] 4.3 实现 deterministic natural-language normalizer，仅覆盖 `SKILL.md` 承诺的固定样例范围，并测试样例到 `action`、`endpoint` 或 `ad_url`、`message` 等命令参数的映射。

## 5. 测试与验证

- [ ] 5.1 增加身份管理单元测试，覆盖首次生成、复用、`ANP_CLIENT_HOME` 覆盖、私钥权限和损坏身份错误。
- [ ] 5.2 增加 URL 安全策略单元测试，覆盖 loopback HTTP、HTTPS 和非 loopback HTTP 拒绝。
- [ ] 5.3 增加 discovery 单元测试，覆盖 AD/OpenRPC 解析、非 ANP 响应、缺少 `chat` 方法、方法列表输出和 `discover --json` 输出结构。
- [ ] 5.4 增加 chat payload 与签名单元测试，覆盖 JSON-RPC `params.message`、非空 id 和签名头生成。
- [ ] 5.5 增加 mock aiohttp 集成测试，验证 `discover --json` 和 `chat --json`，并确认 `chat` 请求携带 DID WBA 签名头。
- [ ] 5.6 增加或扩展真实 Hermes plugin E2E，验证 `anp-client` 可发现服务智能体并通过 `chat --json` 获得 `response`。
- [ ] 5.7 运行客户端 skill 测试、现有 `plugins/anp-agent` 相关测试、格式检查和 lint。
- [ ] 5.8 运行 `openspec validate add-anp-client-skill --type change` 和 `openspec validate --all`，确保变更 artifacts 与整体 specs 有效。

## 6. 收尾

- [ ] 6.1 根据测试结果更新 README/SKILL 故障排查说明，覆盖 DID 文档无法解析、签名无效、缺少认证头、endpoint 安全拒绝和 `serve-did` 仅用于本地开发的边界。
- [ ] 6.2 确认 `clients/anp-client/` 发布包不包含运行态 DID、私钥、临时文件或仓库外软链接。
- [ ] 6.3 通过 `/opsx:verify add-anp-client-skill` 后，再同步 main specs 并归档变更。
