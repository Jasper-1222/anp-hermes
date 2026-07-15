"""ANP 发布压缩包脚本测试。"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "package_anp_release.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("package_anp_release", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_package_release_creates_versioned_and_stable_archives(
    tmp_path: Path,
) -> None:
    """打包脚本生成版本化资产、稳定别名和 LICENSE。"""
    packager = _load_packager()

    result = packager.package_release(root=ROOT, dist_dir=tmp_path, version="9.9.9")

    plugin_zip = tmp_path / "anp-agent-plugin-9.9.9.zip"
    plugin_alias = tmp_path / "anp-agent.zip"
    skill_zip = tmp_path / "anp-client-skill-9.9.9.zip"
    skill_alias = tmp_path / "anp-client.zip"
    assert result == [plugin_zip, plugin_alias, skill_zip, skill_alias]
    assert plugin_alias.read_bytes() == plugin_zip.read_bytes()
    assert skill_alias.read_bytes() == skill_zip.read_bytes()

    with zipfile.ZipFile(plugin_zip) as archive:
        assert archive.namelist() == [
            "README.md",
            "__init__.py",
            "plugin.yaml",
            "pyproject.toml",
            "anp_agent/__init__.py",
            "anp_agent/adapter.py",
            "anp_agent/auth.py",
            "anp_agent/bridge.py",
            "anp_agent/config.py",
            "anp_agent/constants.py",
            "anp_agent/identity.py",
            "anp_agent/server.py",
            "anp_agent/tools.py",
            "LICENSE",
        ]
        assert "MIT License" in archive.read("LICENSE").decode()
        assert "本地 DID resolver base URL" in archive.read("plugin.yaml").decode()

    with zipfile.ZipFile(skill_zip) as archive:
        assert archive.namelist() == [
            "README.md",
            "SKILL.md",
            "requirements.txt",
            "scripts/anp_client.py",
            "scripts/did_identity.py",
            "scripts/did_server.py",
            "scripts/signing.py",
            "LICENSE",
        ]
        assert "MIT License" in archive.read("LICENSE").decode()
        assert (
            "loopback_endpoints_equivalent"
            in archive.read("scripts/anp_client.py").decode()
        )


def test_package_release_preserves_outputs_when_source_preflight_fails(
    tmp_path: Path,
) -> None:
    """源文件预检失败时不得覆盖任何正式发布资产。"""
    packager = _load_packager()
    root = tmp_path / "repo"
    plugin_root = root / "plugins" / "anp-agent"
    skill_root = root / "clients" / "anp-client"
    for relative in packager.PLUGIN_FILES:
        source = plugin_root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(relative, encoding="utf-8")
    for relative in packager.SKILL_FILES:
        source = skill_root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(relative, encoding="utf-8")
    (root / "LICENSE").write_text("MIT License", encoding="utf-8")
    (skill_root / packager.SKILL_FILES[-1]).unlink()

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    output_names = [
        "anp-agent-plugin-9.9.9.zip",
        "anp-agent.zip",
        "anp-client-skill-9.9.9.zip",
        "anp-client.zip",
    ]
    for name in output_names:
        (dist_dir / name).write_bytes(b"sentinel")

    with pytest.raises(FileNotFoundError, match="缺少发布文件"):
        packager.package_release(root=root, dist_dir=dist_dir, version="9.9.9")

    assert all((dist_dir / name).read_bytes() == b"sentinel" for name in output_names)


def test_validate_archive_rejects_runtime_identity_files(tmp_path: Path) -> None:
    """发布包校验拒绝 DID、私钥和缓存产物。"""
    packager = _load_packager()
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("did.json", "{}")
        archive.writestr("private_key.pem", "fake")
        archive.writestr("__pycache__/module.pyc", b"fake")

    errors = packager.validate_archive(bad_zip)

    assert "禁止打包运行态身份或缓存文件: did.json" in errors
    assert "禁止打包运行态身份或缓存文件: private_key.pem" in errors
    assert "禁止打包运行态身份或缓存文件: __pycache__/module.pyc" in errors


def test_validate_archive_rejects_absolute_local_paths_and_private_keys(
    tmp_path: Path,
) -> None:
    """发布包校验拒绝本机绝对路径和真实私钥块。"""
    packager = _load_packager()
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("README.md", "path=/home/peter/anp-hermes\nwin=/mnt/c/tmp")
        archive.writestr(
            "key.txt",
            "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----\n",
        )

    errors = packager.validate_archive(bad_zip)

    assert "禁止打包本机绝对路径引用: README.md" in errors
    assert "禁止打包真实私钥块: key.txt" in errors
