"""ANP 插件身份管理模块测试。"""

import json
import os
import stat
from pathlib import Path

import pytest

from anp_agent.identity import (
    _is_valid_did,
    load_or_create_identity,
)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """提供临时数据目录。"""
    return tmp_path / "anp-agent"


def test_first_call_generates_identity(tmp_data_dir: Path) -> None:
    """首次调用应生成新身份并持久化到数据目录。"""
    identity = load_or_create_identity(tmp_data_dir, "localhost")

    assert identity.did.startswith("did:wba:")
    assert identity.private_key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")

    did_path = tmp_data_dir / "did.json"
    key_path = tmp_data_dir / "private_key.pem"
    assert did_path.exists()
    assert key_path.exists()

    loaded_doc = json.loads(did_path.read_text(encoding="utf-8"))
    assert loaded_doc["id"] == identity.did


def test_second_call_loads_existing_identity(tmp_data_dir: Path) -> None:
    """第二次调用应加载已有身份，不重复生成。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    second = load_or_create_identity(tmp_data_dir, "localhost")

    assert second.did == first.did
    assert second.private_key_pem == first.private_key_pem
    assert second.did_document == first.did_document


def test_private_key_permission(tmp_data_dir: Path) -> None:
    """私钥文件权限应为 0o600。"""
    load_or_create_identity(tmp_data_dir, "localhost")
    key_path = tmp_data_dir / "private_key.pem"
    mode = key_path.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_identity_uses_expanded_explicit_data_dir(tmp_path: Path) -> None:
    """显式数据目录可使用 ~，且身份文件写入展开后的目录。"""
    home = tmp_path / "home"
    data_dir = "~/hermes-data/anp-agent"
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        identity = load_or_create_identity(data_dir, "localhost")
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home

    expected_dir = home / "hermes-data" / "anp-agent"
    assert identity.data_dir == expected_dir
    assert (expected_dir / "did.json").exists()
    key_path = expected_dir / "private_key.pem"
    assert key_path.exists()
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600


def test_identity_regenerates_in_same_explicit_data_dir(tmp_data_dir: Path) -> None:
    """身份损坏后应在同一显式数据目录备份并重新生成。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    did_path = tmp_data_dir / "did.json"
    did_path.write_text("not-json", encoding="utf-8")

    second = load_or_create_identity(tmp_data_dir, "localhost")

    assert second.data_dir == tmp_data_dir
    assert second.did != first.did
    assert (tmp_data_dir / "private_key.pem").exists()
    assert len(list(tmp_data_dir.glob("did.json.bak.*"))) == 1


def test_corrupt_did_document_backup_and_regenerate(tmp_data_dir: Path) -> None:
    """DID 文档损坏时应自动备份并重新生成。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    did_path = tmp_data_dir / "did.json"

    # 写入非法 JSON
    did_path.write_text("not-json", encoding="utf-8")

    second = load_or_create_identity(tmp_data_dir, "localhost")

    # 重新生成，DID 应不同
    assert second.did != first.did
    backups = list(tmp_data_dir.glob("did.json.bak.*"))
    assert len(backups) == 1


def test_corrupt_did_structure_backup_and_regenerate(tmp_data_dir: Path) -> None:
    """DID 格式非法时应自动备份并重新生成。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    did_path = tmp_data_dir / "did.json"

    # 保留合法 JSON 但 id 非法
    bad_doc = {"id": "did:example:bad", "verificationMethod": []}
    did_path.write_text(json.dumps(bad_doc), encoding="utf-8")

    second = load_or_create_identity(tmp_data_dir, "localhost")

    assert second.did != first.did
    assert second.did.startswith("did:wba:")
    backups = list(tmp_data_dir.glob("did.json.bak.*"))
    assert len(backups) == 1


def test_missing_private_key_regenerates(tmp_data_dir: Path) -> None:
    """私钥缺失时应自动重新生成。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    key_path = tmp_data_dir / "private_key.pem"

    key_path.unlink()

    second = load_or_create_identity(tmp_data_dir, "localhost")

    assert second.did != first.did
    assert key_path.exists()


def test_corrupt_private_key_backup_and_regenerate(tmp_data_dir: Path) -> None:
    """私钥内容损坏时应备份旧私钥并重新生成身份。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")
    key_path = tmp_data_dir / "private_key.pem"
    key_path.write_bytes(b"not-a-private-key")

    second = load_or_create_identity(tmp_data_dir, "localhost")

    assert second.did != first.did
    assert key_path.exists()
    assert second.private_key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")
    assert len(list(tmp_data_dir.glob("private_key.pem.bak.*"))) == 1


def test_hostname_change_regenerates(tmp_data_dir: Path) -> None:
    """hostname 变化时应重新生成身份以保持 DID 一致性。"""
    first = load_or_create_identity(tmp_data_dir, "localhost")

    second = load_or_create_identity(tmp_data_dir, "service.example.com")

    assert "service.example.com" in second.did
    assert second.did != first.did


def test_is_valid_did() -> None:
    """DID 格式校验基本覆盖。"""
    assert _is_valid_did("did:wba:localhost:agent:e1_abc123") is True
    assert _is_valid_did("did:example:bad") is False
    assert _is_valid_did("not-a-did") is False
    assert _is_valid_did("did:wba") is False
    assert _is_valid_did(123) is False  # type: ignore[arg-type]
