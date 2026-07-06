"""ANP 插件服务端认证模块测试。"""

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anp.authentication import create_did_wba_document
from anp.authentication import did_wba_verifier as did_wba_verifier_module
from anp.authentication.did_resolver import resolve_did_document
from anp.authentication.did_wba import resolve_did_wba_document
from anp.authentication.did_wba_verifier import DidWbaVerifierError

from auth import AuthenticationError, create_auth
from identity import ANPIdentity, load_or_create_identity
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

    caller_did = await auth.authenticate("POST", target_url, headers, body)

    assert caller_did == caller_identity["did"]


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
        cause = exc_info.value.__cause__
        assert cause is not None
        assert "resolve" in str(cause).lower() or "timeout" in str(cause).lower()
    finally:
        did_wba_verifier_module.resolve_did_wba_document = original_resolver
        os.environ.pop("ANP_DID_RESOLVE_TIMEOUT", None)


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
    from auth import _classify_verifier_error

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
