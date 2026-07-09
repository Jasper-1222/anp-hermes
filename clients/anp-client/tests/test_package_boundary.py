"""anp-client skill 安装包边界测试。"""

from __future__ import annotations

from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {"did.json", "private_key.pem"}
FORBIDDEN_SUFFIXES = (".tmp", ".bak")
FORBIDDEN_ABSOLUTE_PATH = "/home/peter/" + "anp-hermes"


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


def test_skill_scripts_do_not_depend_on_repo_absolute_path() -> None:
    offenders: list[Path] = []
    for path in CLIENT_ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".md", ".txt"}:
            if FORBIDDEN_ABSOLUTE_PATH in path.read_text(encoding="utf-8"):
                offenders.append(path)
    assert offenders == []
