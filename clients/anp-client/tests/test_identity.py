"""个人智能体 DID WBA 身份测试。"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from did_identity import (
    IdentityError,
    client_home as resolve_client_home,
    load_identity,
    load_or_create_identity,
)


def test_client_home_uses_anp_client_home(client_home: Path) -> None:
    assert resolve_client_home() == client_home
    assert resolve_client_home().name == "anp-client-home"


def test_load_or_create_identity_creates_files(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)

    assert identity.did.startswith("did:wba:")
    assert identity.did_path == client_home / "did.json"
    assert identity.key_path == client_home / "private_key.pem"
    assert identity.did_path.exists()
    assert identity.key_path.exists()
    assert identity.did_document["id"] == identity.did
    assert "keyAgreement" not in identity.did_document


def test_load_or_create_identity_reuses_existing_identity(client_home: Path) -> None:
    first = load_or_create_identity(client_home)
    second = load_or_create_identity(client_home)

    assert second.did == first.did
    assert second.did_document == first.did_document


def test_private_key_permission_is_0600(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)

    mode = stat.S_IMODE(identity.key_path.stat().st_mode)
    assert mode == 0o600


def test_load_identity_successfully_loads_existing_identity(client_home: Path) -> None:
    created = load_or_create_identity(client_home)

    loaded = load_identity(client_home)

    assert loaded.did == created.did
    assert loaded.did_document == created.did_document
    assert loaded.did_path == created.did_path
    assert loaded.key_path == created.key_path


def test_load_identity_fails_when_no_identity_exists(client_home: Path) -> None:
    with pytest.raises(IdentityError, match="未找到个人智能体身份"):
        load_identity(client_home)


def test_load_or_create_fails_when_only_did_exists(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text(
        '{"id":"did:wba:localhost:agent:e1_missing"}', encoding="utf-8"
    )

    with pytest.raises(IdentityError, match="身份文件不完整"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_did_json_is_invalid(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text("not-json", encoding="utf-8")
    (client_home / "private_key.pem").write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_did_json_is_not_utf8(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_bytes(b"\xff\xfe")
    (client_home / "private_key.pem").write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_did_document_has_no_id(client_home: Path) -> None:
    client_home.mkdir(parents=True)
    (client_home / "did.json").write_text(json.dumps({"not_id": "x"}), encoding="utf-8")
    (client_home / "private_key.pem").write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档缺少 id"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_private_key_pem_is_invalid(
    client_home: Path,
) -> None:
    identity = load_or_create_identity(client_home)
    identity.key_path.write_text("not-a-real-key", encoding="utf-8")

    with pytest.raises(IdentityError, match="私钥 PEM 无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_private_key_pem_is_encrypted(
    client_home: Path,
) -> None:
    identity = load_or_create_identity(client_home)
    encrypted_pem = Ed25519PrivateKey.generate().private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(b"passphrase"),
    )
    identity.key_path.write_bytes(encrypted_pem)

    with pytest.raises(IdentityError, match="私钥 PEM 无法解析"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_authentication_is_missing(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)
    doc = dict(identity.did_document)
    doc.pop("authentication", None)
    identity.did_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(IdentityError, match="DID 文档缺少 authentication"):
        load_or_create_identity(client_home)


def test_load_or_create_fails_when_private_key_does_not_match_did_document(
    client_home: Path, tmp_path: Path
) -> None:
    first = load_or_create_identity(client_home)
    second_home = tmp_path / "second-home"
    second = load_or_create_identity(second_home)
    shutil.copyfile(second.key_path, first.key_path)

    with pytest.raises(IdentityError, match="私钥与 DID 文档不匹配"):
        load_or_create_identity(client_home)


def test_private_key_permission_is_repaired_before_mismatch_error(
    client_home: Path, tmp_path: Path
) -> None:
    first = load_or_create_identity(client_home)
    second_home = tmp_path / "second-home"
    second = load_or_create_identity(second_home)
    shutil.copyfile(second.key_path, first.key_path)
    first.key_path.chmod(0o644)

    with pytest.raises(IdentityError, match="私钥与 DID 文档不匹配"):
        load_or_create_identity(client_home)

    mode = stat.S_IMODE(first.key_path.stat().st_mode)
    assert mode == 0o600
