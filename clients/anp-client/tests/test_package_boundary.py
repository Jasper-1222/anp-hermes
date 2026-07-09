"""anp-client skill 安装包边界测试。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CLIENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CLIENT_ROOT.parents[1]
FORBIDDEN_NAMES = {"did.json", "private_key.pem"}
FORBIDDEN_SUFFIXES = (".tmp", ".bak")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s'\"`(])(?:/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+|[A-Za-z]:[\\/][^\s'\"`)]*)"
)
_ALLOWED_ABSOLUTE_PREFIXES = ("/agent/", "~/.anp-client")


def _contains_forbidden_absolute_path(text: str) -> bool:
    if str(REPO_ROOT) in text:
        return True
    for match in _ABSOLUTE_PATH_RE.finditer(text):
        candidate = match.group(0).strip(" \t\n'\"`(")
        if not candidate.startswith(_ALLOWED_ABSOLUTE_PREFIXES):
            return True
    return False


@pytest.mark.parametrize(
    "text",
    [
        "/home/alice/project/clients/anp-client/scripts/anp_client.py",
        "/Users/alice/project/clients/anp-client/scripts/anp_client.py",
        "C:\\Users\\alice\\project\\clients\\anp-client\\scripts\\anp_client.py",
        "D:/work/project/clients/anp-client/scripts/anp_client.py",
    ],
)
def test_detects_generic_absolute_paths(text: str) -> None:
    assert _contains_forbidden_absolute_path(text)


@pytest.mark.parametrize(
    "text",
    [
        "python3 scripts/anp_client.py discover --endpoint http://127.0.0.1:8900",
        "默认身份目录为 ~/.anp-client/，可通过 ANP_CLIENT_HOME 覆盖。",
        "GET /agent/ad.json 和 POST /agent/rpc",
    ],
)
def test_allows_documented_relative_and_runtime_paths(text: str) -> None:
    assert not _contains_forbidden_absolute_path(text)


def test_skill_package_contains_required_root_files() -> None:
    for relative in ["SKILL.md", "README.md", "requirements.txt", "scripts"]:
        assert (CLIENT_ROOT / relative).exists()


def test_skill_package_contains_no_runtime_identity_files() -> None:
    forbidden = [
        path
        for path in CLIENT_ROOT.rglob("*")
        if path.name in FORBIDDEN_NAMES or path.name.endswith(FORBIDDEN_SUFFIXES)
    ]
    assert forbidden == []


def test_skill_package_contains_no_symlinks() -> None:
    assert [path for path in CLIENT_ROOT.rglob("*") if path.is_symlink()] == []


def _packaged_text_files() -> list[Path]:
    packaged_roots = [
        CLIENT_ROOT / "SKILL.md",
        CLIENT_ROOT / "README.md",
        CLIENT_ROOT / "requirements.txt",
        CLIENT_ROOT / "requirements-dev.txt",
        CLIENT_ROOT / "scripts",
    ]
    files: list[Path] = []
    for root in packaged_roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix in {".py", ".md", ".txt"}
            )
    return files


def test_skill_scripts_do_not_depend_on_repo_absolute_path() -> None:
    offenders = [
        path
        for path in _packaged_text_files()
        if _contains_forbidden_absolute_path(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
