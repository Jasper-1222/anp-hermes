"""ANP 插件 DID WBA 身份管理模块。

本模块负责生成、加载和持久化 did:wba 身份，为 ANPAuth 和平台适配器提供身份支持。
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from anp.authentication import create_did_wba_document

# 私钥文件权限
_PRIVATE_KEY_MODE = 0o600
_PUBLIC_KEY_MODE = 0o644


def _atomic_write_text(path: Path, text: str, mode: int) -> None:
    """以指定权限原子写入文本文件。

    先写入同目录临时文件，再 rename 覆盖目标文件，保证崩溃时不会留下半写文件；
    使用 os.open(..., O_CREAT | O_WRONLY, mode) 在创建时即应用权限，
    避免 `write -> chmod` 之间的竞态导致文件短暂可读。
    """
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as f:
            f.write(text)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    """以指定权限原子写入二进制文件。"""
    tmp_path = path.with_name(f"{path.name}.tmp")
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    fd = os.open(tmp_path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(data)
    finally:
        os.close(fd)
    os.replace(tmp_path, path)


@dataclass(frozen=True)
class ANPIdentity:
    """封装 ANP DID 身份。"""

    did: str
    did_document: dict[str, Any]
    private_key_pem: bytes
    data_dir: Path


# 默认路径名
_DID_DOCUMENT_NAME = "did.json"
_PRIVATE_KEY_NAME = "private_key.pem"


def _save_private_key(path: Path, pem: bytes) -> None:
    """保存私钥 PEM 文件，创建时即设置 0o600 权限。"""
    _atomic_write_bytes(path, pem, _PRIVATE_KEY_MODE)


def _load_private_key(path: Path) -> bytes:
    """读取私钥 PEM 文件。"""
    return path.read_bytes()


def _is_valid_did(did: str) -> bool:
    """校验 DID 基本格式是否为 did:wba:...。"""
    if not isinstance(did, str):
        return False
    parts = did.split(":")
    if len(parts) < 4:
        return False
    return parts[0] == "did" and parts[1] == "wba"


def _is_valid_did_document(doc: Any) -> bool:
    """校验 DID 文档基本结构是否完整。"""
    if not isinstance(doc, dict):
        return False
    did = doc.get("id")
    if not _is_valid_did(did):
        return False
    if not isinstance(doc.get("verificationMethod"), list):
        return False
    # 至少包含 assertionMethod 或 authentication 之一
    if not ("assertionMethod" in doc or "authentication" in doc):
        return False
    return True


def _backup(path: Path) -> Path:
    """将旧文件备份为 <path>.bak.<timestamp>。"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    path.rename(backup_path)
    return backup_path


def _generate_identity(data_dir: Path, hostname: str, endpoint: str | None = None) -> ANPIdentity:
    """调用 ANP SDK 生成新的 DID WBA 身份并持久化。"""
    if endpoint:
        agent_description_url = f"{endpoint.rstrip('/')}/agent/ad.json"
    else:
        agent_description_url = f"https://{hostname}/agent/ad.json"
    did_document, keys = create_did_wba_document(
        hostname=hostname,
        path_segments=["agent"],
        agent_description_url=agent_description_url,
        did_profile="e1",
    )
    private_key_pem = keys["key-1"][0]
    did = did_document["id"]

    data_dir.mkdir(parents=True, exist_ok=True)
    did_path = data_dir / _DID_DOCUMENT_NAME
    key_path = data_dir / _PRIVATE_KEY_NAME

    _atomic_write_text(did_path, json.dumps(did_document, indent=2), _PUBLIC_KEY_MODE)
    _save_private_key(key_path, private_key_pem)

    return ANPIdentity(
        did=did,
        did_document=did_document,
        private_key_pem=private_key_pem,
        data_dir=data_dir,
    )


def _load_identity(data_dir: Path, hostname: str) -> ANPIdentity:
    """从 data_dir 加载已有身份，失败则抛出异常。"""
    did_path = data_dir / _DID_DOCUMENT_NAME
    key_path = data_dir / _PRIVATE_KEY_NAME

    doc_text = did_path.read_text(encoding="utf-8")
    did_document = json.loads(doc_text)

    if not _is_valid_did_document(did_document):
        raise ValueError("DID 文档校验失败")

    # 校验 DID 中的 hostname 是否与当前配置一致
    did = did_document["id"]
    parts = did.split(":")
    if len(parts) < 4 or parts[2] != hostname:
        raise ValueError("DID 中的 hostname 与当前配置不匹配")

    private_key_pem = _load_private_key(key_path)

    # 简单检查私钥 PEM 结构
    if b"-----BEGIN PRIVATE KEY-----" not in private_key_pem:
        raise ValueError("私钥格式非法")

    return ANPIdentity(
        did=did,
        did_document=did_document,
        private_key_pem=private_key_pem,
        data_dir=data_dir,
    )


def load_or_create_identity(
    data_dir: Path | str,
    hostname: str,
    endpoint: str | None = None,
) -> ANPIdentity:
    """加载已有身份；若缺失或损坏则备份旧文件并重新生成。"""
    data_dir_path = Path(data_dir).expanduser()
    did_path = data_dir_path / _DID_DOCUMENT_NAME
    key_path = data_dir_path / _PRIVATE_KEY_NAME

    if did_path.exists() and key_path.exists():
        try:
            return _load_identity(data_dir_path, hostname)
        except (OSError, ValueError, json.JSONDecodeError):
            # 任意损坏场景：备份旧文件后重新生成
            if did_path.exists():
                _backup(did_path)
            if key_path.exists():
                _backup(key_path)
            return _generate_identity(data_dir_path, hostname, endpoint)

    return _generate_identity(data_dir_path, hostname, endpoint)
