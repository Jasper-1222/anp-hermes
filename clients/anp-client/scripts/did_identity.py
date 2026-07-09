"""个人智能体 DID WBA 身份管理。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import base58
from anp.authentication import create_did_wba_document
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_DEFAULT_HOME = Path.home() / ".anp-client"
_DID_FILE = "did.json"
_KEY_FILE = "private_key.pem"
_PRIVATE_KEY_MODE = 0o600
_PUBLIC_FILE_MODE = 0o644
_ED25519_MULTIKEY_PREFIX = b"\xed\x01"


class IdentityError(RuntimeError):
    """个人智能体身份无法创建或加载。"""


@dataclass(frozen=True)
class CallerIdentity:
    """个人智能体 DID WBA 身份。"""

    did: str
    did_document: dict[str, Any]
    did_path: Path
    key_path: Path


def client_home() -> Path:
    """返回个人智能体身份目录。"""
    configured = os.environ.get("ANP_CLIENT_HOME")
    if configured:
        return Path(configured).expanduser()
    return _DEFAULT_HOME


def load_or_create_identity(home: Path | None = None) -> CallerIdentity:
    """加载已有身份；如果身份完全不存在则创建。"""
    root = home or client_home()
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE

    if did_path.exists() and key_path.exists():
        return _load_from_paths(did_path, key_path)
    if did_path.exists() or key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    return _create_identity(root)


def load_identity(home: Path | None = None) -> CallerIdentity:
    """只加载已有身份，不自动创建。"""
    root = home or client_home()
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE
    if not did_path.exists() and not key_path.exists():
        raise IdentityError(f"未找到个人智能体身份: {root}")
    if not did_path.exists() or not key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    return _load_from_paths(did_path, key_path)


def _atomic_write_text(path: Path, text: str, mode: int) -> None:
    """以指定权限原子写入文本文件。"""
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as file:
            file.write(text)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    """以指定权限原子写入二进制文件。"""
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as file:
            file.write(data)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


def _create_identity(root: Path) -> CallerIdentity:
    """创建新的 DID WBA 身份。"""
    root.mkdir(parents=True, exist_ok=True)
    did_path = root / _DID_FILE
    key_path = root / _KEY_FILE
    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
        enable_e2ee=False,
    )
    auth_key = keys.get("key-1")
    if not auth_key:
        raise IdentityError("DID 文档未生成 key-1 认证密钥")
    private_key_pem = auth_key[0]
    _atomic_write_text(
        did_path,
        json.dumps(did_document, indent=2, ensure_ascii=False),
        _PUBLIC_FILE_MODE,
    )
    _atomic_write_bytes(key_path, private_key_pem, _PRIVATE_KEY_MODE)
    return _load_from_paths(did_path, key_path)


def _load_from_paths(did_path: Path, key_path: Path) -> CallerIdentity:
    """从文件加载 DID WBA 身份。"""
    if key_path.exists():
        _chmod_private_key(key_path)
    try:
        did_document = json.loads(did_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityError(f"DID 文档无法解析: {did_path}") from exc
    if not isinstance(did_document, dict):
        raise IdentityError(f"DID 文档必须是 JSON object: {did_path}")
    did = did_document.get("id")
    if not isinstance(did, str) or not did:
        raise IdentityError(f"DID 文档缺少 id: {did_path}")
    if not did.startswith("did:wba:"):
        raise IdentityError(f"个人智能体 DID 必须是 did:wba: {did_path}")
    if not key_path.exists():
        raise IdentityError(f"身份文件不完整: {did_path} / {key_path}")
    private_key = _load_private_key(key_path)
    _validate_did_document_key_match(did_document, private_key, did_path, key_path)
    return CallerIdentity(
        did=did, did_document=did_document, did_path=did_path, key_path=key_path
    )


def _load_private_key(key_path: Path) -> Ed25519PrivateKey:
    """解析 Ed25519 私钥 PEM。"""
    try:
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (TypeError, ValueError) as exc:
        raise IdentityError(f"私钥 PEM 无法解析: {key_path}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise IdentityError(f"私钥不是 Ed25519: {key_path}")
    return key


def _authentication_method_id(did_document: dict[str, Any], did_path: Path) -> str:
    """返回 DID 文档授权的认证 verification method id。"""
    authentication = did_document.get("authentication")
    if not isinstance(authentication, list) or not authentication:
        raise IdentityError(f"DID 文档缺少 authentication: {did_path}")
    first = authentication[0]
    if not isinstance(first, str) or not first:
        raise IdentityError(f"DID 文档 authentication 格式无效: {did_path}")
    return first


def _public_key_multibase(
    did_document: dict[str, Any], method_id: str, did: str, did_path: Path
) -> str:
    """从 verificationMethod 中取出认证公钥。"""
    if not method_id.startswith(f"{did}#"):
        raise IdentityError(f"DID 文档认证方法与 id 不一致: {did_path}")
    methods = did_document.get("verificationMethod")
    if not isinstance(methods, list):
        raise IdentityError(f"DID 文档缺少 verificationMethod: {did_path}")
    for method in methods:
        if isinstance(method, dict) and method.get("id") == method_id:
            if method.get("controller") != did:
                raise IdentityError(
                    f"DID 文档认证方法 controller 与 id 不一致: {did_path}"
                )
            value = method.get("publicKeyMultibase")
            if isinstance(value, str) and value:
                return value
            raise IdentityError(f"DID 文档认证方法缺少 publicKeyMultibase: {did_path}")
    raise IdentityError(
        f"DID 文档 verificationMethod 未包含 authentication: {did_path}"
    )


def _validate_did_document_key_match(
    did_document: dict[str, Any],
    private_key: Ed25519PrivateKey,
    did_path: Path,
    key_path: Path,
) -> None:
    """确认私钥对应 DID 文档 authentication 公钥。"""
    did = did_document["id"]
    method_id = _authentication_method_id(did_document, did_path)
    multibase_value = _public_key_multibase(did_document, method_id, did, did_path)
    if not multibase_value.startswith("z"):
        raise IdentityError(f"DID 文档认证公钥不是 base58btc Multikey: {did_path}")
    try:
        decoded = base58.b58decode(multibase_value[1:])
    except ValueError as exc:
        raise IdentityError(f"DID 文档认证公钥无法解析: {did_path}") from exc
    if not decoded.startswith(_ED25519_MULTIKEY_PREFIX):
        raise IdentityError(f"DID 文档认证公钥不是 Ed25519 Multikey: {did_path}")
    did_public_bytes = decoded[len(_ED25519_MULTIKEY_PREFIX) :]
    private_public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    if did_public_bytes != private_public_bytes:
        raise IdentityError(f"私钥与 DID 文档不匹配: {key_path}")


def _chmod_private_key(key_path: Path) -> None:
    """确保私钥文件仅所有者可读写。"""
    key_path.chmod(_PRIVATE_KEY_MODE)
