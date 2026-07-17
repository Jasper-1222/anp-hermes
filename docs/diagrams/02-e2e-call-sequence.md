# 端到端调用时序图

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 调用方<br/>(anp-client)
    participant Server as ANP Server<br/>(server.py)
    participant Auth as ANPAuth<br/>(auth.py)
    participant Bridge as ANPBridge<br/>(bridge.py)
    participant Adapter as ANPAdapter<br/>(adapter.py)
    participant Hermes as Hermes Core

    %% ===== 阶段 1：服务发现 =====
    rect rgb(227, 242, 253, 0.4)
        Note over Caller,Server: 阶段 1 — 服务发现
        Caller->>Server: GET /agent/ad.json
        Server-->>Caller: 200 Agent Description<br/>{did, endpoint, security, interfaces}
        Caller->>Server: GET /agent/interface.json
        Server-->>Caller: 200 OpenRPC<br/>{methods: [chat, anp.get_capabilities, ...]}
        Caller->>Caller: 验证 protocolType=ANP<br/>提取 rpc_endpoint
    end

    %% ===== 阶段 2：调用准备 =====
    rect rgb(255, 243, 224, 0.4)
        Note over Caller: 阶段 2 — 调用准备（客户端本地）
        Caller->>Caller: 加载调用方身份<br/>(did.json + private_key.pem)
        Caller->>Caller: 构造 JSON-RPC body<br/>{"jsonrpc":"2.0","method":"chat",<br/>"params":{"message":"你好"},"id":"abc-123"}
        Caller->>Caller: DID WBA 签名<br/>DIDWbaAuthHeader.get_auth_header()<br/>→ Signature + Signature-Input 头
    end

    %% ===== 阶段 3：RPC 请求 =====
    rect rgb(232, 245, 233, 0.4)
        Note over Caller,Server: 阶段 3 — JSON-RPC 请求
        Caller->>Server: POST /agent/rpc<br/>headers: Signature, Signature-Input<br/>body: {"jsonrpc":"2.0","method":"chat",...}
        Server->>Server: _parse_rpc_request()<br/>校验 jsonrpc/id/method/params
    end

    %% ===== 阶段 4：身份认证 =====
    rect rgb(243, 229, 245, 0.4)
        Note over Server,Auth: 阶段 4 — DID WBA 身份认证
        Server->>Auth: authenticate(method, url, headers, body)
        Auth->>Auth: DidWbaVerifier.verify_request()
        Auth->>Auth: 1. 解析调用方 DID
        Auth->>Auth: 2. 通过 resolve_did_wba_document()<br/>获取调用方 DID Document
        Auth->>Auth: 3. 验证 HTTP Message Signature
        Auth->>Auth: 4. 验证 proof + binding
        Auth-->>Server: AuthenticationResult<br/>{caller_did, headers(Authentication-Info)}
    end

    %% ===== 阶段 5：桥接 =====
    rect rgb(255, 235, 238, 0.4)
        Note over Server,Bridge: 阶段 5 — JSON-RPC 桥接
        Server->>Bridge: bridge.call(rpc_id, method, params, caller_did)
        Bridge->>Bridge: 生成内部 request_id = "req-1"
        Bridge->>Bridge: 创建 asyncio.Future<br/>存入 _pending["req-1"]
        Bridge->>Bridge: 构造 MessageEvent<br/>{text, message_id, source, metadata}
        Bridge->>Adapter: handle_message(event)
    end

    %% ===== 阶段 6：LLM 处理 =====
    rect rgb(255, 248, 225, 0.4)
        Note over Adapter,Hermes: 阶段 6 — Hermes 消息处理
        Adapter->>Hermes: BasePlatformAdapter.handle_message()
        Hermes->>Hermes: 会话管理 + LLM 推理
        Note right of Hermes: 可能涉及<br/>skills / tools 调用
        Hermes->>Adapter: send(chat_id="anp:req-1", content)
    end

    %% ===== 阶段 7：响应回传 =====
    rect rgb(227, 242, 253, 0.4)
        Note over Adapter,Caller: 阶段 7 — 响应回传
        Adapter->>Bridge: set_result("req-1", content)
        Bridge->>Bridge: Future.set_result(content)<br/>清理 _pending["req-1"]
        Bridge-->>Server: 返回结果文本
        Server->>Server: 构造 JSON-RPC result<br/>{"result":{"response":"..."}}
        Server-->>Caller: HTTP 200<br/>{"jsonrpc":"2.0","id":"abc-123",<br/>"result":{"response":"你好！我是..."}}
    end

    %% ===== 设计要点注释 =====
    Note over Caller,Hermes: 关键设计点：<br/>1. chat_id 格式 "anp:req-N" — Adapter.send() 解析此前缀路由回对应 Future<br/>2. 客户端 JSON-RPC id 与服务端内部 request_id 隔离<br/>3. bridge.call() 使用 asyncio.shield() 防止外部取消污染内部状态<br/>4. 请求超时由 asyncio.wait_for() 保护，超时后清理 pending entry
```

**阶段说明**：
1. **服务发现**（步骤 1-3）— 调用方获取 Agent Description 和 OpenRPC，了解服务能力和接口
2. **调用准备**（步骤 4-5）— 客户端本地加载身份、构造请求、生成 DID WBA 签名
3. **JSON-RPC 请求**（步骤 6-7）— 签名请求到达服务端，首先做格式校验
4. **身份认证**（步骤 8-15）— 解析 DID 文档、验证签名和 proof，提取 caller DID
5. **桥接**（步骤 16-21）— 创建 Future、构造 MessageEvent、注入 Hermes 消息流
6. **LLM 处理**（步骤 22-25）— Hermes 核心消息处理管道（可能涉及 skills/tools）
7. **响应回传**（步骤 26-31）— Future 完成、构造 JSON-RPC 结果、返回调用方
