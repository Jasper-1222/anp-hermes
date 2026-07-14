"""ANP 发布压缩包脚本测试。"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

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


def test_package_release_creates_exact_plugin_and_skill_archives(
    tmp_path: Path,
) -> None:
    """打包脚本生成固定文件清单的 plugin 与 skill zip。"""
    packager = _load_packager()

    result = packager.package_release(root=ROOT, dist_dir=tmp_path, version="9.9.9")

    plugin_zip = tmp_path / "anp-agent-plugin-9.9.9.zip"
    skill_zip = tmp_path / "anp-client-skill-9.9.9.zip"
    assert result == [plugin_zip, skill_zip]
    assert plugin_zip.exists()
    assert skill_zip.exists()

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
        ]
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
        ]
        assert (
            "loopback_endpoints_equivalent"
            in archive.read("scripts/anp_client.py").decode()
        )


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
