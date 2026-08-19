# 组件架构图

```mermaid
graph TD
    %% ========== 样式定义 ==========
    classDef client fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    classDef plugin fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef hermes fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    CLIENT["ANP Client<br/>（调用方智能体）"]:::client
    CALLER_DID["调用方 DID 文档服务<br/>（本地测试：anp-client serve-did）"]:::client
    PLUGIN["Hermes ANP Plugin<br/>（服务端插件）"]:::plugin
    HERMES["Hermes Agent Core"]:::hermes
    EXT["ANP 网络基础设施<br/>（SDK / DID 解析）"]:::external

    CLIENT -->|"HTTP + DID WBA 认证"| PLUGIN
    PLUGIN -->|"发现文档 / RPC 响应"| CLIENT
    PLUGIN -->|"消息桥接"| HERMES
    HERMES -->|"LLM 回复"| PLUGIN
    PLUGIN -->|"认证时解析调用方 DID 文档"| CALLER_DID
    PLUGIN --- EXT
    CLIENT --- EXT
```

**图例**：蓝色 = 调用方（ANP Client / 调用方 DID 文档服务） · 橙色 = Hermes ANP Plugin（服务端） · 绿色 = Hermes Agent Core · 紫色 = 外部依赖

**说明**：DID WBA 认证要求服务端能解析到调用方的 DID 文档。本地测试中由 `anp-client serve-did`（默认 `127.0.0.1:18900`）托管，服务端通过 `ANP_DID_RESOLVER_BASE_URL` 指向它；生产环境则按 DID WBA HTTPS 规则从调用方公开地址解析，无需该角色。
