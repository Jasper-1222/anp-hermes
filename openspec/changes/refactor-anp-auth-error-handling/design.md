## Context

当前 `anp-agent` 的认证错误处理集中在 `plugins/anp-agent/auth.py` 与 `plugins/anp-agent/server.py`：

- `auth.AuthenticationError` 仅包含字符串消息，丢失 `DidWbaVerifierError.status_code`、challenge 响应头与原始异常类型。
- `server._map_auth_error()` 仅通过 `"Failed to resolve DID document"` 子串判断 `-32002`，其余全部映射为 `-32001`。
- 当 `ANP_DID_RESOLVER_BASE_URL` 配置错误时，`aiohttp.ClientError` 被通用 `except Exception` 捕获并包装为 `AuthenticationError("认证失败")`，随后被映射为 `-32001 DID WBA 签名无效`，掩盖了真实原因。

## Goals / Non-Goals

**Goals:**
- 按异常类型与 ANP SDK 错误消息将认证失败分类为 6 个具体 JSON-RPC 错误码。
- 保留并转发安全的 challenge 头，不泄露内部 URL、堆栈或网络错误细节。
- 更新测试，断言具体错误码与消息。

**Non-Goals:**
- 修改 DID WBA 协议本身或 ANP SDK 行为。
- 引入新的外部依赖。
- 处理授权策略（allowlist 逻辑保持现状）。

## Decisions

- **决策 1：扩展 `AuthenticationError` 而非新建异常树**
  - 理由：现有代码大量捕获 `AuthenticationError`，单一异常类加字段改动面最小；同时避免调用方需要学习多个异常类型。
  - 替代方案：为每种错误创建子类。拒绝原因：会增加 except 分支与测试复杂度，且无额外收益。

- **决策 2：在 `auth.py` 内完成分类，server.py 仅做映射**
  - 理由：认证知识应封装在 `ANPAuth` 中，`server.py` 只需读取错误对象元数据构造 JSON-RPC 响应。
  - 替代方案：在 `server.py` 中解析原始异常。拒绝原因：会将 ANP SDK 细节泄漏到 HTTP 层。

- **决策 3：resolver wrapper 把网络错误统一包装为 `DidWbaVerifierError("Failed to resolve DID document: ...")`**
  - 理由：让分类器按消息前缀即可识别，避免新增异常分支。
  - 替代方案：在分类器里单独判断 `aiohttp.ClientError`。拒绝原因：wrapper 已经把底层异常包装过一次，统一前缀更简单。

- **决策 4：仅转发 `WWW-Authenticate` 与 `Accept-Signature` 两个安全 challenge 头**
  - 理由：这两个头是 DID WBA / HTTP Message Signatures 协议定义的挑战头；其他头可能包含内部信息。

## Risks / Trade-offs

- **[Risk] 错误码变化可能影响现有测试脚本或调用方** → 对外错误码从几乎全是 `-32001` 变为更具体的值，属于行为变更。本次变更在调用方视角下错误仍然存在，仅 `code`/`message` 变化；需在 PR 描述中说明。
- **[Risk] `DidWbaVerifierError.message` 文本依赖 ANP SDK 版本** → 分类器应同时参考 `status_code`，并在未知消息时保守回退到 `-32001` 或 `-32006`，避免升级 SDK 后产生未分类错误。
- **[Risk] 同一进程内多个 `ANPAuth` 实例共享 resolver wrapper 全局配置** → 该问题已存在，本次变更不改变其行为；注意测试清理。

## Migration Plan

无需数据迁移或部署步骤。升级插件后，认证失败响应的错误码和消息会更具体，调用方可按需调整错误处理逻辑。

## Open Questions

- 是否需要将新的错误码写入 `README.md` 或 API 文档？（建议作为后续文档任务）
- 是否需要在手动测试脚本 `scripts/anp_chat_client.py` 中增加按错误码提示用户？（建议作为后续改进）
