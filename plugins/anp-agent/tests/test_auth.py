"""ANP 插件服务端认证模块测试。"""

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from anp.authentication import create_did_wba_document
from anp.authentication import did_resolver as did_resolver_module
from anp.authentication import did_wba_verifier as did_wba_verifier_module
from anp.authentication.did_resolver import resolve_did_document
from anp.authentication.did_wba import resolve_did_wba_document
from anp.authentication.did_wba_verifier import DidWbaVerifierError

from anp_agent.auth import (
    _DEFAULT_DID_RESOLVE_TIMEOUT,
    AuthenticationError,
    _resolver_config,
    create_auth,
)
from anp_agent.identity import ANPIdentity, load_or_create_identity
from tests.helpers.did_server import DIDDocumentServer
from tests.helpers.signing import build_signed_headers


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """提供临时数据目录。"""
    return tmp_path / "anp-agent"


@pytest.fixture
def identity(tmp_data_dir: Path) -> ANPIdentity:
    """提供临时服务端身份。"""
    return load_or_create_identity(tmp_data_dir, "localhost")


@pytest.fixture
def caller_identity(tmp_path: Path) -> dict:
    """提供临时调用方身份及文件路径。"""
    workdir = tmp_path / "caller"
    workdir.mkdir(parents=True, exist_ok=True)

    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    did = did_document["id"]
    auth_key = keys.get("key-1")
    assert auth_key is not None, "DID 文档未生成 key-1 认证密钥"
    private_key_pem = auth_key[0]

    did_path = workdir / "did.json"
    key_path = workdir / "private_key.pem"
    did_path.write_text(json.dumps(did_document), encoding="utf-8")
    key_path.write_bytes(private_key_pem)

    return {
        "did": did,
        "did_document": did_document,
        "private_key_pem": private_key_pem,
        "did_path": did_path,
        "key_path": key_path,
    }


@pytest_asyncio.fixture
async def did_server(caller_identity: dict):
    """启动本地 DID 文档服务器，并返回可解析的 base URL。"""
    async with DIDDocumentServer(caller_identity["did_document"]) as server:
        yield server.base_url


@pytest_asyncio.fixture
async def auth(identity: ANPIdentity, did_server: str):
    """构造已配置本地解析器的 ANPAuth 实例。"""
    original_resolver = resolve_did_wba_document

    async def _patched_resolver(did: str, verify_proof: bool = False):
        return await resolve_did_document(
            did,
            base_url_override=did_server,
            verify_proof=verify_proof,
        )

    did_wba_verifier_module.resolve_did_wba_document = _patched_resolver

    auth = create_auth(identity)

    yield auth

    did_wba_verifier_module.resolve_did_wba_document = original_resolver


@pytest.mark.asyncio
async def test_valid_signature_returns_caller_did(auth, caller_identity: dict) -> None:
    """合法签名请求应返回正确的调用方 DID。"""
    target_url = "http://localhost:8900/agent/rpc"
    body = json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {}, "id": "1"})
    headers = await build_signed_headers(caller_identity, target_url, body)

    result = await auth.authenticate("POST", target_url, headers, body)

    assert result.caller_did == caller_identity["did"]
    assert "Authentication-Info" in result.headers


@pytest.mark.asyncio
async def test_authenticate_filters_success_headers(identity: ANPIdentity) -> None:
    """认证成功时只返回允许转发的 Authentication-Info 头。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(
        return_value={
            "did": "did:wba:localhost:agent:caller",
            "response_headers": {
                "authentication-info": 'access_token="token"',
                "Authorization": "Bearer should-not-forward",
                "X-Internal": "should-not-forward",
            },
        }
    )

    try:
        result = await auth.authenticate(
            "POST",
            "http://localhost:8900/agent/rpc",
            {
                "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                "Signature": "sig1=:AAAA:",
            },
            "{}",
        )
    finally:
        auth._verifier.verify_request = original

    assert result.caller_did == "did:wba:localhost:agent:caller"
    assert result.headers == {"Authentication-Info": 'access_token="token"'}


@pytest.mark.asyncio
async def test_authenticate_missing_success_headers_returns_empty_headers(
    identity: ANPIdentity,
) -> None:
    """认证成功但 verifier 未返回响应头时，headers 为空。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(
        return_value={"did": "did:wba:localhost:agent:caller"}
    )

    try:
        result = await auth.authenticate(
            "POST",
            "http://localhost:8900/agent/rpc",
            {
                "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                "Signature": "sig1=:AAAA:",
            },
            "{}",
        )
    finally:
        auth._verifier.verify_request = original

    assert result.headers == {}


@pytest.mark.asyncio
async def test_missing_signature_raises(auth) -> None:
    """缺少认证头时应抛出 -32003。"""
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.authenticate(
            "POST",
            "http://localhost:8900/agent/rpc",
            {"Content-Type": "application/json"},
            "{}",
        )
    assert exc_info.value.rpc_code == -32003
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_signature_raises(auth, caller_identity: dict) -> None:
    """签名无效时应抛出 -32001。"""
    target_url = "http://localhost:8900/agent/rpc"
    body = json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {}, "id": "1"})
    headers = await build_signed_headers(caller_identity, target_url, body)

    headers["Signature"] = "sig1=:invalid_signature:"

    with pytest.raises(AuthenticationError) as exc_info:
        await auth.authenticate("POST", target_url, headers, body)
    assert exc_info.value.rpc_code == -32001


@pytest.mark.asyncio
async def test_unexpected_exception_returns_internal_auth_error(
    identity: ANPIdentity,
) -> None:
    """认证器内部未预期异常应映射为 -32006。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(side_effect=RuntimeError("模拟内部错误"))

    try:
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {"Content-Type": "application/json"},
                "{}",
            )
        assert exc_info.value.rpc_code == -32006
        assert exc_info.value.status_code == 500
    finally:
        auth._verifier.verify_request = original


@pytest.mark.asyncio
async def test_did_resolution_timeout_returns_unresolvable_error(
    identity: ANPIdentity,
) -> None:
    """DID 文档解析超时应映射为 DID 无法解析错误（-32002）。"""
    original_resolver = resolve_did_wba_document

    async def _hanging_resolver(did: str, verify_proof: bool = False):
        await asyncio.sleep(5)
        return {}

    did_wba_verifier_module.resolve_did_wba_document = _hanging_resolver
    os.environ["ANP_DID_RESOLVE_TIMEOUT"] = "0.1"

    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32002
        assert exc_info.value.status_code == 401
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        os.environ.pop("ANP_DID_RESOLVE_TIMEOUT", None)
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None


@pytest.mark.asyncio
async def test_unresolvable_did_raises(identity: ANPIdentity) -> None:
    """DID 文档无法解析时应抛出 -32002。"""
    original_resolver = resolve_did_wba_document

    async def _failing_resolver(did: str, verify_proof: bool = False):
        raise DidWbaVerifierError(
            "Failed to resolve DID document: mocked failure",
            status_code=401,
        )

    did_wba_verifier_module.resolve_did_wba_document = _failing_resolver

    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32002
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver


@pytest.mark.asyncio
async def test_verify_request_missing_did_returns_invalid_signature(
    identity: ANPIdentity,
) -> None:
    """verify_request 返回结果缺少 did 字段时应返回 -32001。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(return_value={})

    try:
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32001
        assert exc_info.value.status_code == 401
    finally:
        auth._verifier.verify_request = original


@pytest.mark.asyncio
async def test_verify_request_non_string_did_returns_invalid_signature(
    identity: ANPIdentity,
) -> None:
    """verify_request 返回 did 字段非字符串时应返回 -32001。"""
    auth = create_auth(identity)

    original = auth._verifier.verify_request
    auth._verifier.verify_request = AsyncMock(return_value={"did": 123})

    try:
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32001
        assert exc_info.value.status_code == 401
    finally:
        auth._verifier.verify_request = original


def test_classify_verifier_error_status_code_500_fallback_to_internal_auth() -> None:
    """status_code 为 500 且消息无法分类时回退到 -32006。"""
    from anp_agent.auth import _classify_verifier_error

    exc = DidWbaVerifierError("unexpected verifier failure", status_code=500)
    message, http_status, rpc_code = _classify_verifier_error(exc)
    assert message == "认证服务内部错误"
    assert http_status == 500
    assert rpc_code == -32006


def test_classify_verifier_error_status_code_500_with_known_message_still_matches() -> None:
    """status_code 为 500 但消息可分类时，仍按已知消息映射。"""
    from anp_agent.auth import _classify_verifier_error

    exc = DidWbaVerifierError("Failed to resolve DID document: timeout", status_code=500)
    _, _, rpc_code = _classify_verifier_error(exc)
    assert rpc_code == -32002


@pytest.mark.parametrize(
    "message,status_code,expected_code",
    [
        ("Failed to resolve DID document: timeout", 401, -32002),
        ("Missing Signature-Input header", 401, -32003),
        ("Missing Signature header", 401, -32003),
        ("Invalid DID document proof", 401, -32004),
        ("Verification method not in authentication", 401, -32005),
        ("Signature verification failed", 401, -32001),
        ("Nonce verification failed", 401, -32001),
    ],
)
def test_classify_verifier_error_maps_known_errors(message, status_code, expected_code) -> None:
    """已知 verifier 错误应映射到正确错误码。"""
    from anp_agent.auth import _classify_verifier_error

    exc = DidWbaVerifierError(message, status_code=status_code)
    _, _, rpc_code = _classify_verifier_error(exc)
    assert rpc_code == expected_code


@pytest.mark.asyncio
async def test_authentication_error_carries_structured_fields() -> None:
    """AuthenticationError 应携带结构化字段。"""
    exc = AuthenticationError(
        "缺少认证头",
        status_code=401,
        rpc_code=-32003,
        headers={"WWW-Authenticate": "test"},
    )
    assert str(exc) == "缺少认证头"
    assert exc.status_code == 401
    assert exc.rpc_code == -32003
    assert exc.headers == {"WWW-Authenticate": "test"}


@pytest.mark.asyncio
async def test_bad_resolver_base_url_returns_unresolvable_error(
    identity: ANPIdentity,
) -> None:
    """错误的 loopback ANP_DID_RESOLVER_BASE_URL 应映射为 -32002。"""
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = "http://127.0.0.1:1"
    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32002
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


@pytest.mark.asyncio
async def test_loopback_resolver_base_url_authenticates_without_manual_patch(
    identity: ANPIdentity,
    caller_identity: dict,
    did_server: str,
) -> None:
    """loopback resolver override 应支持真实签名认证，无需手工 patch SDK resolver。"""
    original_resolver = did_wba_verifier_module.resolve_did_wba_document
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = did_server
    try:
        auth = create_auth(identity)
        target_url = "http://localhost:8900/agent/rpc"
        body = json.dumps({"jsonrpc": "2.0", "method": "chat", "params": {}, "id": "1"})
        headers = await build_signed_headers(caller_identity, target_url, body)

        result = await auth.authenticate("POST", target_url, headers, body)

        assert result.caller_did == caller_identity["did"]
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.com",
        "https://example.com",
    ],
)
def test_non_loopback_resolver_base_url_fails_fast(
    identity: ANPIdentity,
    base_url: str,
) -> None:
    """非 loopback resolver override 应在初始化时失败，避免误用于生产。"""
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = base_url
    try:
        with pytest.raises(ValueError, match="ANP_DID_RESOLVER_BASE_URL"):
            create_auth(identity)
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


@pytest.mark.asyncio
async def test_https_loopback_resolver_override_uses_ssl_verification(
    identity: ANPIdentity,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTPS loopback override 调用通用 resolver 时应保持 verify_ssl=True。"""
    captured = {}

    async def _fake_resolve_did_document(*args, **kwargs):
        captured.update(kwargs)
        raise DidWbaVerifierError("Failed to resolve DID document: mocked", status_code=401)

    monkeypatch.setattr(
        did_resolver_module,
        "resolve_did_document",
        _fake_resolve_did_document,
    )
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = "https://localhost:9443"
    original_resolver = did_wba_verifier_module.resolve_did_wba_document
    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError):
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert captured["verify_ssl"] is True
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


@pytest.mark.parametrize("raw", ["not-a-number", "0", "-1"])
def test_invalid_resolver_timeout_falls_back_to_default(
    identity: ANPIdentity,
    raw: str,
) -> None:
    """非法、零值或负数 timeout 应回退默认值。"""
    os.environ["ANP_DID_RESOLVE_TIMEOUT"] = raw
    try:
        create_auth(identity)
        assert _resolver_config["timeout"] == float(_DEFAULT_DID_RESOLVE_TIMEOUT)
    finally:
        os.environ.pop("ANP_DID_RESOLVE_TIMEOUT", None)
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


def test_excessive_resolver_timeout_is_capped(identity: ANPIdentity) -> None:
    """超大 timeout 应被限制到安全上限。"""
    os.environ["ANP_DID_RESOLVE_TIMEOUT"] = "999999"
    try:
        create_auth(identity)
        assert _resolver_config["timeout"] == 60.0
    finally:
        os.environ.pop("ANP_DID_RESOLVE_TIMEOUT", None)
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


def test_same_resolver_override_configuration_is_idempotent(
    identity: ANPIdentity,
) -> None:
    """相同 resolver override 配置应幂等，不重复嵌套 wrapper。"""
    original_resolver = did_wba_verifier_module.resolve_did_wba_document
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = "http://127.0.0.1:8900"
    try:
        create_auth(identity)
        first_wrapper = did_wba_verifier_module.resolve_did_wba_document
        create_auth(identity)
        second_wrapper = did_wba_verifier_module.resolve_did_wba_document

        assert first_wrapper is second_wrapper
        assert getattr(second_wrapper, "_anp_auth_wrapper", False) is True
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


def test_different_resolver_override_configuration_fails_fast(
    identity: ANPIdentity,
) -> None:
    """不同非空 resolver override 配置不得静默覆盖进程级 wrapper。"""
    original_resolver = did_wba_verifier_module.resolve_did_wba_document
    os.environ["ANP_DID_RESOLVER_BASE_URL"] = "http://127.0.0.1:8900"
    try:
        create_auth(identity)
        os.environ["ANP_DID_RESOLVER_BASE_URL"] = "http://127.0.0.1:8901"
        with pytest.raises(RuntimeError, match="resolver"):
            create_auth(identity)
    finally:
        os.environ.pop("ANP_DID_RESOLVER_BASE_URL", None)
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)


@pytest.mark.asyncio
async def test_invalid_did_document_from_resolver_returns_invalid_document_error(
    identity: ANPIdentity,
) -> None:
    """resolver 返回无效 DID Document 时应映射为 -32004 且不外泄内部细节。"""
    original_resolver = did_wba_verifier_module.resolve_did_wba_document

    async def _invalid_resolver(did: str, verify_proof: bool = False):
        raise ValueError("DID document binding verification failed for http://127.0.0.1:9999")

    did_wba_verifier_module.resolve_did_wba_document = _invalid_resolver
    try:
        auth = create_auth(identity)
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate(
                "POST",
                "http://localhost:8900/agent/rpc",
                {
                    "Signature-Input": 'sig1=("@method");created=1;keyid="did:wba:localhost:agent:e1_x#key-1"',
                    "Signature": "sig1=:AAAA:",
                },
                None,
            )
        assert exc_info.value.rpc_code == -32004
        assert str(exc_info.value) == "DID 文档无效"
        assert "127.0.0.1" not in str(exc_info.value)
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        _resolver_config["timeout"] = 10
        _resolver_config["base_url"] = None
        _resolver_config.pop("verify_ssl", None)
