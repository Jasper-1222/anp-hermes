"""ANP 插件身份管理模块测试。"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

# 插件目录名包含连字符，无法作为 Python 包导入，因此将插件根目录加入搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from identity import (
    ANPIdentity,
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
