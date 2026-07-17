# 错误路径与错误码全景

```mermaid
graph TD
    classDef parse fill:#ffcdd2,stroke:#c62828
    classDef auth fill:#fff9c4,stroke:#f9a825
    classDef binding fill:#e1bee7,stroke:#8e24aa
    classDef route fill:#b3e5fc,stroke:#0277bd
    classDef bridge fill:#ffccbc,stroke:#d84315
    classDef tool fill:#c8e6c9,stroke:#2e7d32

    %% 入口
    START(["POST /agent/rpc"]) --> PARSE

    %% ===== 请求体解析 =====
    subgraph PARSE_SECTION[" "]
        PARSE["请求体解析"]
        PARSE --> P1{"UTF-8 解码"}
        P1 -- 失败 --> PE["HTTP 400<br/>-32700 Parse error<br/>JSON 解析失败"]
        P1 -- 成功 --> P2{"JSON 解析"}
        P2 -- 失败 --> PE
        P2 -- 成功 --> P3{"jsonrpc == '2.0'"}
        P3 -- 否 --> IR["HTTP 400<br/>-32600 Invalid Request<br/>无效的 JSON-RPC 版本"]
        P3 -- 是 --> P4{"id 非空字符串"}
        P4 -- 否 --> IR
        P4 -- 是 --> P5{"method 为字符串"}
        P5 -- 否 --> IR
        P5 -- 是 --> P6{"params 为对象"}
        P6 -- 否 --> IR
        P6 -- 是 --> AUTH
    end

    %% ===== 认证 =====
    subgraph AUTH_SECTION[" "]
        AUTH["ANPAuth.authenticate()"]
        AUTH --> A1{"签名头存在"}
        A1 -- 否 --> E32003["HTTP 401 / -32003<br/>缺少认证头"]
        A1 -- 是 --> A2{"DID 文档可解析"}
        A2 -- 超时/网络错误 --> E32002["HTTP 401 / -32002<br/>DID 文档无法解析"]
        A2 -- 是 --> A3{"DID 文档有效"}
        A3 -- proof/binding 无效 --> E32004["HTTP 401 / -32004<br/>DID 文档无效"]
        A3 -- 是 --> A4{"认证方法已授权"}
        A4 -- VM 不在 authentication --> E32005["HTTP 403 / -32005<br/>认证方法未授权"]
        A4 -- 是 --> A5{"签名验证通过"}
        A5 -- 否 --> E32001["HTTP 401 / -32001<br/>DID WBA 签名无效"]
        A5 -- 是 --> A6{"无内部异常"}
        A6 -- 异常 --> E32006["HTTP 500 / -32006<br/>认证服务内部错误"]
        A6 -- 是 --> ROUTE
    end

    %% ===== Core Binding 校验 =====
    subgraph BINDING_SECTION[" "]
        ROUTE["方法路由"]
        ROUTE --> M1{"方法类型"}
        M1 -- "chat (含 meta/body)" --> CB1{"meta.profile 支持"}
        CB1 -- 否 --> E1001["HTTP 200 / 1001<br/>不支持的 ANP profile<br/>anp.unsupported_profile"]
        CB1 -- 是 --> CB2{"meta.security_profile 支持"}
        CB2 -- 否 --> E1002["HTTP 200 / 1002<br/>不支持的安全 profile<br/>anp.unsupported_security_profile"]
        CB2 -- 是 --> CB3{"params.meta/body 结构"}
        CB3 -- 无效 --> E1003["HTTP 200 / 1003<br/>params 形态无效<br/>anp.invalid_params_shape"]
        CB3 -- 有效 --> BRIDGE
    end

    %% ===== 方法路由（续） =====
    M1 -- "anp.get_capabilities" --> CAP["直接返回能力声明"]
    M1 -- "hermes.tool.*" --> TOOL_START
    M1 -- 其他 --> E32601["HTTP 200 / -32601<br/>方法不存在"]

    %% ===== 桥接 =====
    subgraph BRIDGE_SECTION[" "]
        BRIDGE["bridge.call()"]
        BRIDGE --> B1{"pending 容量"}
        B1 -- 满 --> E32603A["HTTP 200 / -32603<br/>服务繁忙"]
        B1 -- 有余 --> B2{"message_handler 正常"}
        B2 -- 异常 --> E32603B["HTTP 200 / -32603<br/>无法将请求提交给 Hermes"]
        B2 -- 正常 --> B3{"Future 在超时前完成"}
        B3 -- 超时 --> E32603C["HTTP 200 / -32603<br/>请求处理超时"]
        B3 -- 完成 --> SUCCESS["HTTP 200<br/>{"result":{"response":"..."}}"]
    end

    %% ===== Tool RPC =====
    subgraph TOOL_SECTION[" "]
        TOOL_START["ToolRPCDispatcher.call_tool()"]
        TOOL_START --> T1{"tool_rpc 已启用"}
        T1 -- 否 --> T32601A["HTTP 200 / -32601<br/>方法不存在<br/>（无工具暴露）"]
        T1 -- 是 --> T2{"caller DID 已授权"}
        T2 -- 否 --> T32601B["HTTP 200 / -32601<br/>方法不存在<br/>（无 DID 泄露）"]
        T2 -- 是 --> T3{"工具在 allowlist 且<br/>不在 denylist"}
        T3 -- 否 --> T32601C["HTTP 200 / -32601<br/>方法不存在"]
        T3 -- 是 --> T4{"参数校验通过"}
        T4 -- 否 --> E32602["HTTP 200 / -32602<br/>工具参数无效"]
        T4 -- 是 --> T5{"执行结果"}
        T5 -- 超时 --> E32603T1["HTTP 200 / -32603<br/>anp.tool_timeout"]
        T5 -- 结果过大 --> E32603T2["HTTP 200 / -32603<br/>anp.tool_result_too_large"]
        T5 -- 执行异常 --> E32603T3["HTTP 200 / -32603<br/>anp.tool_failed"]
        T5 -- 成功 --> TOOL_SUCCESS["HTTP 200<br/>{"result":{"content":...}}"]
    end

    %% 样式
    class PE,IR parse
    class E32001,E32002,E32003,E32004,E32005,E32006 auth
    class E1001,E1002,E1003 binding
    class E32601,T32601A,T32601B,T32601C route
    class E32603A,E32603B,E32603C bridge
    class E32602,E32603T1,E32603T2,E32603T3 tool
```

## 错误码速查表

| HTTP | JSON-RPC Code | ANP Code | 含义 | 触发阶段 |
|------|-------------|----------|------|---------|
| 400 | -32700 | — | JSON 解析失败 | 请求体解析 |
| 400 | -32600 | — | 无效请求（版本/id/method/params） | 请求体解析 |
| 401 | -32001 | — | DID WBA 签名无效 | 认证 |
| 401 | -32002 | — | DID 文档无法解析（超时/网络） | 认证 |
| 401 | -32003 | — | 缺少认证头 | 认证 |
| 401 | -32004 | — | DID 文档无效（proof/binding） | 认证 |
| 403 | -32005 | — | 认证方法未授权 | 认证 |
| 500 | -32006 | — | 认证服务内部错误 | 认证 |
| 200 | 1001 | `anp.unsupported_profile` | 不支持的 ANP profile | Core Binding |
| 200 | 1002 | `anp.unsupported_security_profile` | 不支持的安全 profile | Core Binding |
| 200 | 1003 | `anp.invalid_params_shape` | params 形态无效 | Core Binding |
| 200 | -32601 | — | 方法不存在 | 方法路由 |
| 200 | -32602 | — | 工具参数无效 | Tool RPC |
| 200 | -32603 | `anp.tool_timeout` | 工具执行超时 | Tool RPC |
| 200 | -32603 | `anp.tool_result_too_large` | 工具结果过大 | Tool RPC |
| 200 | -32603 | `anp.tool_failed` | 工具执行失败 | Tool RPC |
| 200 | -32603 | — | 内部错误（繁忙/超时/handler异常） | 桥接 |

**设计说明**：
- HTTP 400 仅在请求体无法解析时返回（JSON-RPC 2.0 规范要求）；认证失败返回 401/403/500，其他所有业务错误返回 HTTP 200 但携带 JSON-RPC error
- `-32001` 至 `-32006` 为 ANP 插件自定义错误码（JSON-RPC 保留范围 -32000 至 -32099）
- `1001`-`1003` 为 ANP Core Binding 公共错误码，携带 `error.data.anp_code` 辅助客户端分类
- Tool RPC 的 `-32601`（方法不存在）不会泄露工具是否存在或 caller DID 是否授权
