## Context

`anp-agent` 当前已经完成 DID WBA 认证、JSON-RPC `chat`、`anp.get_capabilities`、Agent Description、well-known discovery、包化发布、测试隔离与 resolver 生产边界。现阶段对外 ANP 能力仍是“对话型服务智能体”：调用方可以发起 `chat`，但无法以机器可读、结构化 RPC 方式调用 Hermes 已注册的 tools / skills。

Hermes 的工具系统运行在 Hermes 进程内，工具通过全局 registry 注册，正常 Agent 会基于 toolsets 生成模型可见工具列表，并通过 `model_tools.handle_function_call()` 执行工具调用。平台适配器和 `MessageEvent` 本身不直接携带 tool registry，因此本变更需要在 `anp-agent` 内新增一层受控的 tool exposure/dispatch 边界，而不是把远程 ANP 请求直接透传到底层 registry。

关键约束：

- 插件必须继续零侵入 Hermes 核心。
- DID WBA 认证仍是 `/agent/rpc` 的前置条件。
- 默认不得向远程调用方开放任何 Hermes tool。
- 高风险工具（shell、代码执行、文件写入、skill 管理、外部发布等）不得默认开放。
- OpenRPC、Agent Description 和 `anp.get_capabilities` 只能声明当前真实启用并 allowlisted 的 tools。

## Goals / Non-Goals

**Goals:**

- 新增一套默认关闭的 ANP tool RPC 能力，使远程调用方可以调用明确 allowlisted 的 Hermes tools。
- 使用稳定命名空间将 Hermes tool 映射为 ANP OpenRPC methods，避免与 `chat`、`anp.*` 方法冲突。
- 动态生成 OpenRPC method 文档，并在 discovery/capabilities 中只声明已启用工具。
- 在执行工具前完成 caller DID、工具名、toolset、denylist、参数 schema、超时和结果大小边界校验。
- 复用 Hermes `model_tools.handle_function_call()`，保留 Hermes tool middleware / hooks / transform 流程，避免直接调用底层 `registry.dispatch()`。
- 为工具调用输出审计日志/元数据，便于追踪 caller DID、request id、tool name 和执行结果。

**Non-Goals:**

- 不修改 Hermes 核心或 fork Hermes 工具系统。
- 不把所有 Hermes tools 自动暴露给 ANP。
- 不默认暴露 shell、代码执行、文件写入、skill 管理、浏览器自动化、外部发布或未知副作用工具。
- 不实现 AP2 支付、E2EE、Direct/Group profile 或多 agent registry。
- 不让远程调用方通过 params 任意加载 skill 或控制 Hermes auto-skill。
- 不保证所有 Hermes tools 都适合无交互远程调用；缺少会话/审批上下文的工具必须保持不可用或显式拒绝。

## Decisions

### Decision 1: 使用显式开关和 allowlist，默认关闭 tool RPC

新增配置建议挂在 `gateway.platforms.anp.extra.tool_rpc` 下：

```yaml
gateway:
  platforms:
    anp:
      extra:
        tool_rpc:
          enabled: false
          allowed_dids: []
          allowed_toolsets: []
          allowed_tools: []
          denied_tools: []
          timeout_seconds: 30
          max_result_bytes: 65536
```

`enabled` 默认为 `false`；即使开启，也必须至少配置 `allowed_tools` 或 `allowed_toolsets`，且 caller DID 必须满足 `allowed_dids`（或后续明确定义的 allow-all 测试开关）。

替代方案是沿用 Hermes 平台 toolsets 自动暴露全部平台可见工具。该方案省配置，但远程 DID 可以直接触达本地工具能力，风险过高，因此不采用。

### Decision 2: 公共 RPC 方法名使用 `hermes.tool.<tool_name>`

对外 OpenRPC method 使用稳定前缀：

```text
hermes.tool.<registry_tool_name>
```

例如 Hermes registry 中的 `skills_list` 可映射为：

```text
hermes.tool.skills_list
```

这样可以避免与 `chat`、`anp.get_capabilities`、未来 `anp.*` 协议方法或普通业务方法冲突。配置 allowlist 仍使用 Hermes registry tool name，而不是带前缀的 RPC method name。

替代方案是直接把 registry tool name 作为 JSON-RPC method。该方案更短，但命名冲突和协议边界不清晰，因此不采用。

### Decision 3: OpenRPC 动态声明只来自已启用且 allowlisted 的工具

`/agent/interface.json` 在构建 OpenRPC 文档时，从当前配置解析工具暴露策略，只将通过以下过滤的工具写入 methods：

1. tool RPC 已启用；
2. 工具属于允许的 toolset 或工具名在 allowlist 中；
3. 工具名不在 denylist 和内置高风险 denylist 中；
4. Hermes check_fn 判定该工具当前可用；
5. 工具 schema 可转换为 OpenRPC 参数说明。

当 tool RPC 未启用或无可暴露工具时，OpenRPC 继续只包含 `chat` 与 `anp.get_capabilities`。

### Decision 4: 调用路径复用 `model_tools.handle_function_call()`，禁止直接 `registry.dispatch()`

工具执行 helper 在通过本地 allowlist 校验后，调用 Hermes 的 `model_tools.handle_function_call()`，而不是直接调用 `tools.registry.registry.dispatch()`。

原因：

- `handle_function_call()` 更接近 Hermes 正常 Agent 工具入口；
- 可保留 pre/post tool hooks、middleware、结果 transform 和 Tool Search bridge 相关逻辑；
- 直接 `registry.dispatch()` 过于底层，会绕过多处安全/观测扩展点。

由于 `handle_function_call()` 对直接传入的工具名不会自动 enforce 当前 ANP allowlist，`anp-agent` 必须在调用前自行校验工具名。

### Decision 5: aiohttp handler 中通过异步边界执行工具调用

工具执行可能是同步、阻塞或长耗时操作。`/agent/rpc` handler 不应直接在 event loop 中执行阻塞工具调用。

实现时应使用 `asyncio.to_thread()` 或等效 executor，并在 ANP tool RPC 层增加：

- per-call timeout；
- 最大并发数；
- 最大请求参数大小；
- 最大结果大小；
- 取消时的清理与 JSON-RPC error 映射。

### Decision 6: 错误映射不泄露未授权工具信息

对外错误语义：

- 未知 method 或未暴露/未授权工具：JSON-RPC `-32601 Method not found`；
- 参数不符合工具 schema：JSON-RPC `-32602 Invalid params`；
- 工具执行失败、超时、被取消、结果过大：JSON-RPC `-32603 Internal error` 或带安全 `error.data.anp_code` 的结构化错误；
- DID WBA 认证失败仍沿用现有认证错误码。

未授权工具按 method not found 处理，避免通过差异化错误枚举本地可用工具。

### Decision 7: 审计记录默认不写入敏感参数

每次 tool RPC 调用应记录：

- caller DID；
- JSON-RPC id；
- 服务端 request id；
- registry tool name；
- RPC method name；
- 成功/失败状态；
- 错误类别；
- 耗时。

默认不记录完整参数和完整结果，避免把密钥、prompt、文件内容或第三方响应写入日志。调试模式如需记录参数，必须另设显式开关并在文档中标注风险。

## Risks / Trade-offs

- **远程工具调用扩大攻击面** → 默认关闭、显式 allowlist、内置 denylist、caller DID gate、参数 schema 校验、结果大小限制。
- **`handle_function_call()` 仍缺少完整 Agent 会话上下文** → 首期只支持无交互、低风险、上下文需求明确的工具；需要审批或强会话上下文的工具保持拒绝。
- **工具 schema 与 OpenRPC schema 不完全一致** → 首期采用 best-effort 转换；无法转换的工具不声明、不开放。
- **Hermes 内部 API 变化风险** → 将 Hermes tool access 封装在单独 helper 中，失败时禁用 tool RPC 并在 OpenRPC/capabilities 中不声明工具。
- **动态 tools 导致接口文档随配置变化** → discovery/capabilities 必须实时反映当前配置，测试覆盖启用/关闭两种状态。
- **高风险工具误配置** → 内置 denylist 优先级高于 allowlist；文档明确不建议生产暴露 shell、文件写入、skill 管理和外部副作用工具。

## Migration Plan

1. 新增配置结构与默认值，确保未配置时行为与当前版本完全一致。
2. 新增 tool exposure helper，在测试中用 fake Hermes tool provider 验证 allowlist、schema 与调度，不依赖真实高风险工具。
3. 扩展 OpenRPC、Agent Description 和 `anp.get_capabilities`，但仅在 tool RPC 启用时声明新能力。
4. 扩展 `/agent/rpc` 方法路由，处理 `hermes.tool.*` 方法。
5. 更新 README / CLAUDE / OpenSpec 执行状态，说明默认关闭、安全配置和不建议暴露的工具类型。

回滚策略：将 `tool_rpc.enabled` 保持为 `false` 或移除配置即可恢复为仅 `chat` / `anp.get_capabilities` 的现有行为。

## Open Questions

- Hermes 是否会为平台适配器提供更稳定的官方 tool invocation API？若上游后续提供，应优先迁移到公开接口。
- 首期是否只开放 `skills_list` / `skill_view` 这类只读工具，还是允许用户配置任意低风险工具？建议实现层保留通用 allowlist，但文档示例只展示只读工具。
- 是否需要为不同 caller DID 配置不同工具集合？建议数据结构预留 per-DID 策略，但首期可先实现全局 allowlist + caller DID allowlist。
