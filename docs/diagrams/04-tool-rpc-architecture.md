# Hermes Tool RPC 安全架构

## 五层安全策略

```mermaid
graph TD
    classDef layer1 fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    classDef layer2 fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    classDef layer3 fill:#b3e5fc,stroke:#0277bd,stroke-width:2px
    classDef layer4 fill:#e1bee7,stroke:#8e24aa,stroke-width:2px
    classDef layer5 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef success fill:#a5d6a7,stroke:#2e7d32,stroke-width:3px
    classDef reject fill:#ef9a9a,stroke:#c62828,stroke-width:2px
    classDef builtin fill:#ffcc80,stroke:#e65100

    START(["POST /agent/rpc<br/>method='hermes.tool.xxx'"]) --> L1

    subgraph L1_SECTION[" "]
        L1["第一层：配置开关"]
        L1 --> L1_CHECK{"tool_rpc.enabled"}
        L1_CHECK -- "= false" --> R1["拒绝：-32601<br/>工具 RPC 默认关闭<br/>不泄露任何工具存在性"]
        L1_CHECK -- "= true" --> L2
    end

    subgraph L2_SECTION[" "]
        L2["第二层：调用方授权"]
        L2 --> L2_CHECK{"caller_did 在<br/>allowed_dids 中"}
        L2_CHECK -- 否 --> R2["拒绝：-32601<br/>无 DID 泄露<br/>与工具不存在同行为"]
        L2_CHECK -- 是 --> L3
    end

    subgraph L3_SECTION[" "]
        L3["第三层：工具 Allowlist"]
        L3 --> L3_CHECK{"工具在 allowed_tools<br/>或 allowed_toolsets 中"}
        L3_CHECK -- 否 --> R3["拒绝：-32601<br/>显式 allowlist 必须<br/>不存在的不暴露"]
        L3_CHECK -- 是 --> L4
    end

    subgraph L4_SECTION[" "]
        L4["第四层：工具 Denylist（优先级高于 Allowlist）"]
        L4 --> L4_CHECK{"工具不在 denylist<br/>且不在内置高风险清单"}
        L4_CHECK -- 命中 --> R4["拒绝：-32601<br/>denylist 优先于 allowlist"]

        subgraph BUILTIN["内置 HIGH_RISK_TOOL_DENYLIST"]
            HL["terminal / execute_code<br/>write_file / patch<br/>skill_manage / browser_click<br/>browser_type / browser_file_upload<br/>browser_run_code_unsafe"]
        end

        L4_CHECK -- 未命中 --> L5
    end

    subgraph L5_SECTION[" "]
        L5["第五层：参数校验 + 执行 + 结果限制"]
        L5 --> L5A{"JSON Schema<br/>参数校验通过"}
        L5A -- 否 --> R5A["-32602<br/>工具参数无效<br/>（不泄露内部细节）"]

        L5A -- 是 --> L5B["invoke_hermes_tool()<br/>（通过 asyncio.to_thread<br/>在线程池中执行）"]
        L5B --> L5C{"执行结果"}

        L5C -- 超时<br/>(timeout_seconds) --> R5B["-32603<br/>anp.tool_timeout<br/>retryable=true"]
        L5C -- 结果过大<br/>('>' max_result_bytes) --> R5C["-32603<br/>anp.tool_result_too_large<br/>retryable=false"]
        L5C -- 执行异常 --> R5D["-32603<br/>anp.tool_failed<br/>内部细节不泄露"]
        L5C -- 成功 --> SUCCESS["返回结果<br/>{"result":{"content":...,<br/>"tool":"xxx",<br/>"metadata":{...}}}"]
    end

    L4_CHECK --> BUILTIN

    %% 审计记录
    AUDIT["审计回调（可选）<br/>记录: caller_did, tool,<br/>status, duration_ms<br/>不记录: params, result"]

    SUCCESS --> AUDIT
    R5B --> AUDIT
    R5C --> AUDIT
    R5D --> AUDIT

    %% 样式
    class L1,L1_CHECK layer1
    class L2,L2_CHECK layer2
    class L3,L3_CHECK layer3
    class L4,L4_CHECK layer4
    class L5,L5A,L5B,L5C layer5
    class R1,R2,R3,R4,R5A,R5B,R5C,R5D reject
    class SUCCESS success
    class HL builtin
```

## 配置结构

```yaml
gateway:
  platforms:
    anp:
      extra:
        tool_rpc:
          enabled: false            # 第一层：主开关，默认关闭
          allowed_dids: []          # 第二层：调用方 DID 白名单
          allowed_tools: []         # 第三层：工具白名单（显式允许）
          allowed_toolsets: []      # 第三层：工具集白名单
          denied_tools: []          # 第四层：工具黑名单（优先于白名单）
          timeout_seconds: 30       # 第五层：单次工具调用超时
          max_result_bytes: 65536   # 第五层：结果大小上限（64KB）
```

## 开启前后对比

### 默认关闭状态

`GET /agent/interface.json` 返回的方法列表：

```json
{
  "methods": ["chat", "anp.get_capabilities"]
}
```

`GET /agent/ad.json` 的 `capabilities` 字段不包含 `hermes_tools`。

### 开启并配置 Allowlist 后

```yaml
tool_rpc:
  enabled: true
  allowed_dids:
    - did:wba:localhost:agent:e1_AbCdEf12345
  allowed_tools:
    - skills_list
    - session_info
```

`GET /agent/interface.json` 返回的方法列表：

```json
{
  "methods": [
    "chat",
    "anp.get_capabilities",
    "hermes.tool.skills_list",
    "hermes.tool.session_info"
  ]
}
```

`GET /agent/ad.json` 新增 `capabilities.hermes_tools`：

```json
{
  "capabilities": {
    "hermes_tools": {
      "enabled": true,
      "max_result_bytes": 65536,
      "timeout_seconds": 30
    }
  }
}
```

## 设计原则

1. **默认拒绝** — 所有能力默认关闭，需显式配置才能开启
2. **纵深防御** — 五层独立校验，任何一层失败都返回 `-32601`（不泄露内部状态）
3. **Denylist 优先** — 内置高风险清单不可绕过，即使管理员误配置 allowlist 也能兜底
4. **结果安全** — 超时、过大、异常均返回安全的 `-32603`，不泄露内部调用栈
5. **审计就绪** — 提供 `audit_callback` 注入点，不记录参数/结果中的敏感内容
6. **线程池隔离** — 工具函数可能是阻塞的，通过 `asyncio.to_thread()` 在线程池中执行，避免阻塞事件循环
