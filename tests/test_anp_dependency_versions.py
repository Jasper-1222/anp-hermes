"""ANP SDK 依赖版本边界测试。"""

from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANP_DEP = "anp>=0.8.9,<0.9.0"
EXPECTED_ANP_API_DEP = "anp[api]>=0.8.9,<0.9.0"


def _anp_version_satisfies_baseline(raw: str) -> bool:
    """按 PEP 440 判断 ANP 版本是否位于当前支持区间。"""
    installed = Version(raw)
    return Version("0.8.9") <= installed < Version("0.9.0")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0.8.9.post1", True),
        ("0.8.9+local", True),
        ("0.8.9rc1", False),
    ],
)
def test_anp_version_baseline_uses_pep440(raw: str, expected: bool) -> None:
    """ANP 版本边界遵循 PEP 440 的预发布与本地版本语义。"""
    assert _anp_version_satisfies_baseline(raw) is expected


def test_installed_anp_version_satisfies_current_baseline() -> None:
    """当前验证环境安装的 ANP SDK 满足项目版本边界。"""
    assert _anp_version_satisfies_baseline(version("anp"))


def test_plugin_anp_dependency_uses_current_baseline() -> None:
    """Hermes plugin 运行时与测试 extras 使用相同 ANP 版本边界。"""
    pyproject = ROOT / "plugins" / "anp-agent" / "pyproject.toml"

    text = pyproject.read_text(encoding="utf-8")

    assert f'"{EXPECTED_ANP_DEP}"' in text
    assert f'"{EXPECTED_ANP_API_DEP}"' in text


def test_client_skill_anp_dependency_uses_current_baseline() -> None:
    """OpenClaw skill requirements 使用当前 ANP 版本边界。"""
    requirements = ROOT / "clients" / "anp-client" / "requirements.txt"

    lines = requirements.read_text(encoding="utf-8").splitlines()

    assert EXPECTED_ANP_DEP in lines


def test_release_skill_zip_contains_current_anp_dependency(tmp_path: Path) -> None:
    """发布脚本生成的 skill zip 内包含当前 ANP 版本边界。"""
    import importlib.util
    import sys
    import zipfile

    script_path = ROOT / "scripts" / "package_anp_release.py"
    spec = importlib.util.spec_from_file_location("package_anp_release", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module.package_release(root=ROOT, dist_dir=tmp_path, version="9.9.9")
    skill_zip = tmp_path / "anp-client-skill-9.9.9.zip"

    with zipfile.ZipFile(skill_zip) as archive:
        requirements = archive.read("requirements.txt").decode("utf-8")

    assert re.search(r"^anp>=0\.8\.9,<0\.9\.0$", requirements, re.MULTILINE)
