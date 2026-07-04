# ANP SDK API 与 Hermes handle_message/send 契约调研

> **调研目标**：在实现 `ANPAuth`（Task 6）和 `ANPAdapter`（Task 7）之前，确认 ANP Python SDK 的实际 API 用法与 Hermes `BasePlatformAdapter` 的调用契约，避免基于假设实现。
>
> **ANP SDK 版本**：`anp>=0.8.8,<0.9.0`（实际验证使用 `0.8.8`）
> **Hermes 源码**：`/home/peter/hermes-agent`（本地副本，与已安装 hermes 程序一致）
> **调研日期**：2026-07-04

---

## 1. ANP SDK：生成 `did:wba:` 身份

### 1.1 入口函数

```python
from anp.authentication import create_did_wba_document

did_document, keys = create_did_wba_document(
    hostname="service.example.com",      # 不能是 IP 地址
    port=None,                           # 可选端口
    path_segments=["agent"],             # 可选路径段，e1 会在末尾追加 key binding
    agent_description_url="https://service.example.com/agent/ad.json",
    services=None,
    proof_purpose="assertionMethod",
    verification_method=None,
    domain=None,
    challenge=None,
    created=None,
    enable_e2ee=True,                    # 默认生成 E2EE 密钥（#key-2、#key-3）
    did_profile="e1",                    # e1 | k1 | plain_legacy
    additional_verification_methods=None,
    additional_authentication=None,
)
```

**来源**：`agent-network-protocol/anp/anp/authentication/did_wba.py:500`

### 1.2 返回值

| 名称 | 类型 | 说明 |
|---|---|---|
| `did_document` | `Dict[str, Any]` | 完整 DID 文档，含 `@context`、`id`、`verificationMethod`、`authentication`、`assertionMethod`、`proof` 等 |
| `keys` | `Dict[str, Tuple[bytes, bytes]]` | 以 fragment 为 key，值为 `(private_pem_bytes, public_pem_bytes)` |

`did_profile="e1"` 时，认证主密钥 fragment 为 `"key-1"`，类型为 `Multikey`，使用 Ed25519；同时生成 `key-2`（secp256r1）和 `key-3`（X25519）用于 E2EE。本插件第一期关闭 E2EE，因此只需使用 `key-1`。

### 1.3 DID 格式示例

```text
did:wba:service.example.com:agent:e1_<base64url_fingerprint>
```

- 第 1 段固定为 `did`
- 第 2 段固定为 `wba`
- 第 3 段为 hostname
- 第 4 段起为 path segments；`e1` profile 下，最后一个 segment 为 `e1_<公钥 fingerprint>`

### 1.4 验证过的最小用法

```python
did_document, keys = create_did_wba_document(
    hostname="localhost",
    path_segments=["agent"],
    agent_description_url="https://localhost/agent/ad.json",
    did_profile="e1",
)
did = did_document["id"]
private_key_bytes = keys["key-1"][0]
```

> **风险点**：`hostname` 不接受 IP 地址，测试环境需使用 `localhost` 或域名。

---

## 2. ANP SDK：客户端构造 HTTP Message Signature

### 2.1 入口类

```python
from anp.authentication import DIDWbaAuthHeader

auth = DIDWbaAuthHeader(
    did_document_path="/path/to/did.json",
    private_key_path="/path/to/private_key.pem",
    auth_mode="http_signatures",  # 默认值
)
```

**来源**：`agent-network-protocol/anp/anp/authentication/did_wba_authenticator.py:20`

### 2.2 获取请求头

```python
headers = auth.get_auth_header(
    server_url="https://service.example.com/agent/rpc",
    force_new=False,
    method="POST",
    headers={"Content-Type": "application/json"},
    body=json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {"message": "hi"}, "id": "1"}),
)
```

返回字典包含：

- `Signature-Input`
- `Signature`
- 如 body 非空，还会包含 `Content-Digest`

### 2.3 返回示例

```text
Signature-Input: sig1=("@method" "@target-uri" "@authority" "content-digest");created=1783116656;expires=1783116956;nonce="...";keyid="did:wba:...#key-1"
Signature: sig1=:<base64_signature>:
Content-Digest: sha-256=:<base64_digest>:
```

### 2.4 行为说明

- 如果缓存了该 domain 的 Bearer token 且 `force_new=False`，直接返回 `Authorization: Bearer <token>`。
- 否则按照 `auth_mode` 生成新的签名头。
- `auth_mode` 可选值：`http_signatures`（默认）、`auto`（同 `http_signatures`）、`legacy_didwba`。

---

## 3. ANP SDK：服务端验证 HTTP Message Signature

### 3.1 入口类与配置

```python
from anp.authentication.did_wba_verifier import DidWbaVerifier, DidWbaVerifierConfig

config = DidWbaVerifierConfig(
    jwt_private_key="-----BEGIN PRIVATE KEY-----\n...",  # 可选，但签名验证成功后需要它来签发 access token
    jwt_public_key="-----BEGIN PUBLIC KEY-----\n...",    # 可选，Bearer 验证时需要
    jwt_algorithm="RS256",
    access_token_expire_minutes=60,
    nonce_expiration_minutes=6,
    timestamp_expiration_minutes=5,
    external_nonce_validator=None,
    allowed_domains=None,
    allow_http_signatures=True,
    allow_legacy_didwba=True,
    emit_authentication_info_header=True,
    emit_legacy_authorization_header=True,
    require_nonce_for_http_signatures=True,
)

verifier = DidWbaVerifier(config)
```

**来源**：`agent-network-protocol/anp/anp/authentication/did_wba_verifier.py:47`

### 3.2 验证请求

```python
result = await verifier.verify_request(
    method="POST",
    url="https://service.example.com/agent/rpc",
    headers=headers,  # 包含 Signature-Input / Signature / Content-Digest
    body=request_body,
    domain="service.example.com",  # 可选，默认从 url 提取
)
```

### 3.3 成功返回结构

```python
{
    "did": "did:wba:...",
    "auth_scheme": "http_signatures",  # 或 "legacy_didwba" / "bearer"
    "response_headers": {
        "Authentication-Info": 'access_token="...", token_type="Bearer", expires_in=3600',
        "Authorization": "Bearer ...",
    },
    "access_token": "...",
    "token_type": "bearer",
}
```

### 3.4 异常

```python
class DidWbaVerifierError(Exception):
    def __init__(self, message, status_code=400, headers=None):
        ...
```

常见错误码：

| 场景 | `status_code` |
|---|---|
| 缺少认证头 | 401 |
| 无法解析 DID 文档 | 401 |
| 签名无效 | 401 |
| 时间窗口/Nonce 无效 | 401 |
| 验证方法未授权 | 403 |
| JWT 私钥未配置（签发 token 时） | 500 |
| JWT 公钥未配置（验证 Bearer 时） | 500 |

### 3.5 DID 文档解析路径

- `DidWbaVerifier.verify_request` 内部调用 `resolve_did_wba_document(did)`。
- `resolve_did_wba_document` 会硬编码 HTTPS 请求：`https://{domain}/<path_segments>/did.json`。
- `resolve_did_document(did, base_url_override=...)` 支持覆盖 base URL，但 `DidWbaVerifier` 并未使用它。

> **风险点**：插件在生产环境必须公开托管 DID 文档，或者使用 monkey-patch / 自定义 verifier 来支持非标准解析。测试环境中需在本地启动 DID 文档服务器。

### 3.6 验证过的最小服务端流程

```python
# 临时替换 resolver，让 verifier 从本地测试服务器解析 DID
did_wba_verifier.resolve_did_wba_document = patched_resolver

result = await verifier.verify_request(
    method="POST",
    url=target_url,
    headers={**auth_headers, "Content-Type": "application/json"},
    body=body,
    domain="localhost",
)
caller_did = result["did"]
```

完整示例见：`/home/peter/anp-hermes/.worktrees/feature-anp-agent/scripts/verify_anp_sdk.py`

---

## 4. Hermes 平台适配器契约

### 4.1 关键数据类

#### `MessageType`

```python
from gateway.platforms.base import MessageType

# TEXT, LOCATION, PHOTO, VIDEO, AUDIO, VOICE, DOCUMENT, STICKER, COMMAND
```

**来源**：`/home/peter/.hermes/hermes-agent/gateway/platforms/base.py:1694`

#### `MessageEvent`

```python
@dataclass
class MessageEvent:
    text: str
    message_type: MessageType = MessageType.TEXT
    source: SessionSource = None
    raw_message: Any = None
    message_id: Optional[str] = None
    platform_update_id: Optional[int] = None
    media_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    reply_to_text: Optional[str] = None
    reply_to_author_id: Optional[str] = None
    reply_to_author_name: Optional[str] = None
    reply_to_is_own_message: bool = False
    auto_skill: Optional[str | list[str]] = None
    channel_prompt: Optional[str] = None
    channel_context: Optional[str] = None
    internal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
```

**来源**：`/home/peter/.hermes/hermes-agent/gateway/platforms/base.py:1716`

#### `SessionSource`

```python
@dataclass
class SessionSource:
    platform: Platform
    chat_id: str
    chat_name: Optional[str] = None
    chat_type: str = "dm"
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    thread_id: Optional[str] = None
    chat_topic: Optional[str] = None
    user_id_alt: Optional[str] = None
    chat_id_alt: Optional[str] = None
    is_bot: bool = False
    scope_id: Optional[str] = None
    guild_id: Optional[str] = None
    parent_chat_id: Optional[str] = None
    message_id: Optional[str] = None
    role_authorized: bool = False
    profile: Optional[str] = None
    delivered_via_upstream_relay: bool = False
```

**来源**：`/home/peter/.hermes/hermes-agent/gateway/session.py:122`

#### `SendResult`

```python
@dataclass
class SendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Any = None
    retryable: bool = False
    retry_after: Optional[int] = None
    continuation_message_ids: Optional[List[str]] = None
    error_kind: Optional[str] = None
```

**来源**：`/home/peter/.hermes/hermes-agent/gateway/platforms/base.py:1855`

### 4.2 `BasePlatformAdapter` 抽象接口

```python
class BasePlatformAdapter(ABC):
    def __init__(self, config: PlatformConfig, platform: Platform):
        ...

    @property
    def is_connected(self) -> bool:
        return self._running

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._message_handler = handler

    @abstractmethod
    async def connect(self, *, is_reconnect: bool = False) -> bool: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send(self, chat_id, content, reply_to=None, metadata=None) -> SendResult: ...

    async def handle_message(self, event: MessageEvent) -> None:
        # 非抽象；默认会调用 self._message_handler(event)
        ...

    @abstractmethod
    async def get_chat_info(self, chat_id) -> Dict[str, Any]: ...

    def build_source(self, chat_id, chat_name=None, chat_type="dm", user_id=None,
                     user_name=None, thread_id=None, ...) -> SessionSource:
        ...
```

**来源**：`/home/peter/.hermes/hermes-agent/gateway/platforms/base.py:2863`

### 4.3 `handle_message` 调用时机

Hermes Gateway Runner 在启动平台时：

```python
adapter.set_message_handler(self._handle_message)
success = await adapter.connect()
```

即适配器不需要主动调用 `_handle_message`；当外部事件到达时，适配器应构造 `MessageEvent` 并调用 `self._message_handler(event)`。但在 ANP 插件中，事件由 HTTP 请求触发，因此应直接调用 `self._message_handler(event)`，或通过 `self.handle_message(event)`（其默认实现会调用 `_message_handler`）。

**来源**：`/home/peter/.hermes/hermes-agent/gateway/run.py:6786`

### 4.4 `send` 调用时机

Hermes Agent Core 生成回复后，会调用适配器的 `send(chat_id, content, ...)`。ANP 插件需在 `send` 中根据 `chat_id` 前缀 `anp:` 找到对应 Future 并设置结果。

```python
async def send(self, chat_id: str, content: str, reply_to=None, metadata=None) -> SendResult:
    if chat_id.startswith("anp:") and self._bridge:
        rpc_id = chat_id.split(":", 1)[1]
        self._bridge.set_result(rpc_id, content)
        return SendResult(success=True, message_id=rpc_id)
    return SendResult(success=False, error="unknown chat_id")
```

### 4.5 `chat_id` 自定义

`chat_id` 是平台定义字符串，无固定格式。本插件使用 `anp:{rpc_id}` 作为 `SessionSource.chat_id`，其中 `rpc_id` 来自 JSON-RPC 请求的 `id` 字段。

### 4.6 注册平台

```python
from hermes_cli.plugins import PluginContext

def register(ctx: PluginContext) -> None:
    ctx.register_platform(
        name="anp",
        label="ANP Agent",
        adapter_factory=lambda cfg: ANPAdapter(cfg),
        check_fn=check_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        required_env=["ANP_ALLOW_ALL_USERS"],
        install_hint="pip install anp aiohttp",
        max_message_length=4000,
        emoji="🌐",
        platform_hint="你是一个通过 ANP 协议被其他智能体调用的 Hermes 服务智能体。",
        allowed_users_env="ANP_ALLOWED_USERS",
        allow_all_env="ANP_ALLOW_ALL_USERS",
    )
```

**来源**：`/home/peter/.hermes/hermes-agent/hermes_cli/plugins.py:882`

`register_platform` 的 `**entry_kwargs` 会转发给 `PlatformEntry`。

### 4.7 `is_connected`

`BasePlatformAdapter.is_connected` 已实现为 `self._running`，通过 `_mark_connected()` / `_mark_disconnected()` 切换。子类无需覆盖，只需在 `connect()` 成功后调用 `_mark_connected()`。

---

## 5. 验证脚本运行结果

**脚本**：`/home/peter/anp-hermes/.worktrees/feature-anp-agent/scripts/verify_anp_sdk.py`

**运行时间**：2026-07-04  
**Python 版本**：3.12.3  
**ANP SDK 版本**：`anp==0.8.8`

运行输出摘要：

```text
INFO: 工作目录: /tmp/anp-verify-fhe_kywi
INFO: 生成调用方 DID: did:wba:localhost:agent:e1_JO34eDZPtq7NYqtascYH3VlUDXzd8-otxDwPhJiVY64
INFO: DID 文档服务器已启动: http://127.0.0.1:8765/agent/e1_.../did.json
INFO: resolve_did_document(base_url_override) 成功
INFO: DIDWbaAuthHeader 生成签名头成功
INFO: Signature-Input: sig1=("@method" "@target-uri" "@authority" "content-digest");created=...;keyid="did:wba:localhost:agent:e1_...#key-1"
INFO: DidWbaVerifier 验证成功，返回 access_token
INFO: Bearer token 验证成功
INFO: 所有验证通过。
```

**结论**：
- `create_did_wba_document(..., did_profile="e1")` 可生成完整 DID 文档与 Ed25519 私钥。
- `DIDWbaAuthHeader` 可生成 RFC 9421 风格的 HTTP Message Signature 头。
- `DidWbaVerifier.verify_request()` 可解析 DID 文档、验证签名并签发 JWT access token。
- Bearer token 可复用于后续请求验证。
- `resolve_did_wba_document` 不支持 `base_url_override`；测试中通过 monkey-patch 本地 DID 文档服务器成功绕过。

---

## 6. 与 `aiohttp` 的兼容性

ANP SDK 的 `resolve_did_document`、`DidWbaVerifier.verify_request` 都是 `async` 函数，使用 `aiohttp` 进行 HTTP 请求，与插件的 `aiohttp` 服务器完全兼容。

`DIDWbaAuthHeader.get_auth_header` 是同步函数，只涉及本地签名和文件读取，可在任意上下文中调用。

---

## 6. 风险与待确认点

| 编号 | 风险/待确认点 | 缓解措施 |
|---|---|---|
| R1 | `DidWbaVerifier.verify_request` 内部使用 `resolve_did_wba_document`，不支持 `base_url_override`，测试和生产必须能真实解析 DID | 测试时启动本地 DID 服务器；生产时插件公开自己的 DID 文档 |
| R2 | `DidWbaVerifierConfig` 即使只做签名验证，也需要配置 `jwt_private_key` 才能签发 access token | 插件启动时生成或加载稳定的 RSA 密钥对 |
| R3 | `create_did_wba_document` 不接受 IP 地址作为 hostname | 测试使用 `localhost`，生产使用真实域名 |
| R4 | Hermes 的 allowlist 默认拒绝未授权用户 | 测试环境设置 `ANP_ALLOW_ALL_USERS=1` |
| R5 | `handle_message` 默认实现是非抽象的，但插件应直接构造 `MessageEvent` 并触发 handler | 使用 `self.handle_message(event)` 或 `self._message_handler(event)` |
| R6 | `send` 回调是异步的，且可能在不同 task 中调用 | Bridge 需线程安全地操作 Future |
| R7 | `Platform` 枚举未包含 `"anp"`，构造 `Platform("anp")` 会抛 `ValueError` | Hermes `Platform._missing_()` 仅对 `plugins/platforms/` 下已发现的 bundle 插件或运行时在 `platform_registry` 注册过的插件创建伪成员。ANP 插件必须在 `register(ctx)` 中调用 `ctx.register_platform(name="anp", ...)` 完成注册；注册后 `Platform("anp")` 可正常工作 |
| R8 | `DidWbaVerifier` 默认要求 `require_nonce_for_http_signatures=True`；首次签名请求会消耗 nonce，重复请求会失败 | 测试时若需要重放同一请求，应配置 `require_nonce_for_http_signatures=False`，或确保每次请求使用新 nonce |

---

## 7. 结论

1. ANP SDK 的 DID 生成、HTTP Message Signature 构造、服务端验证 API 均可用，且与 `aiohttp` 兼容。
2. `DidWbaVerifier` 需要真实可解析的 DID 文档 URL；测试环境需本地 DID 服务器。
3. Hermes `BasePlatformAdapter` 的 `handle_message`/`send` 契约清晰：`handle_message` 入队事件，`send` 根据 `chat_id` 返回结果。
4. `chat_id` 可自定义，`anp:{rpc_id}` 方案可行。
5. 注册平台使用 `ctx.register_platform(...)`，额外 kwargs 可配置 `emoji`、`platform_hint`、`allow_all_env` 等。
6. `is_connected` 由基类实现，子类通过 `_mark_connected()` / `_mark_disconnected()` 控制。

以上结论均来自源码阅读和临时脚本 `scripts/verify_anp_sdk.py` 的实际运行。
