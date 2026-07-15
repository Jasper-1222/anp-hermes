#!/usr/bin/env python3
"""构建 ANP Hermes plugin 与 OpenClaw skill 发布压缩包。"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

PLUGIN_FILES = [
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

SKILL_FILES = [
    "README.md",
    "SKILL.md",
    "requirements.txt",
    "scripts/anp_client.py",
    "scripts/did_identity.py",
    "scripts/did_server.py",
    "scripts/signing.py",
]

FORBIDDEN_SUFFIXES = (".pem", ".pyc")
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"
    r"[\s\S]+?"
    r"-----END (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"
)


def _validate_release_sources(
    source_root: Path,
    files: list[str],
    license_path: Path,
) -> None:
    """在写正式产物前确认固定清单与 LICENSE 均存在。"""
    for relative in files:
        source = source_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"缺少发布文件: {source}")
    if not license_path.is_file():
        raise FileNotFoundError(f"缺少许可证文件: {license_path}")


def _write_archive(
    archive_path: Path,
    source_root: Path,
    files: list[str],
    license_path: Path,
) -> None:
    """按固定文件清单写入 zip，并在归档根加入 LICENSE。"""
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for relative in files:
            source = source_root / relative
            if not source.is_file():
                raise FileNotFoundError(f"缺少发布文件: {source}")
            archive.write(source, relative)
        if not license_path.is_file():
            raise FileNotFoundError(f"缺少许可证文件: {license_path}")
        archive.write(license_path, "LICENSE")


def validate_archive(archive_path: Path) -> list[str]:
    """检查发布包是否误包含运行态文件、缓存、本机路径或真实私钥。"""
    errors: list[str] = []
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            parts = set(Path(name).parts)
            if (
                name.startswith("/")
                or ".." in Path(name).parts
                or name.endswith(FORBIDDEN_SUFFIXES)
                or name.endswith("did.json")
                or ".coverage" in parts
                or FORBIDDEN_PARTS.intersection(parts)
            ):
                errors.append(f"禁止打包运行态身份或缓存文件: {name}")

            text = archive.read(name).decode("utf-8", errors="ignore")
            if "/home/peter/" in text or "/mnt/c/" in text:
                errors.append(f"禁止打包本机绝对路径引用: {name}")
            if PRIVATE_KEY_RE.search(text):
                errors.append(f"禁止打包真实私钥块: {name}")
    return errors


def package_release(
    root: Path | None = None,
    dist_dir: Path | None = None,
    version: str = "0.1.0",
) -> list[Path]:
    """生成 plugin 与 skill 发布 zip，并执行边界校验。"""
    repo_root = root or Path(__file__).resolve().parents[1]
    output_dir = dist_dir or repo_root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    plugin_zip = output_dir / f"anp-agent-plugin-{version}.zip"
    plugin_alias = output_dir / "anp-agent.zip"
    skill_zip = output_dir / f"anp-client-skill-{version}.zip"
    skill_alias = output_dir / "anp-client.zip"
    license_path = repo_root / "LICENSE"
    plugin_root = repo_root / "plugins" / "anp-agent"
    skill_root = repo_root / "clients" / "anp-client"

    _validate_release_sources(plugin_root, PLUGIN_FILES, license_path)
    _validate_release_sources(skill_root, SKILL_FILES, license_path)

    _write_archive(
        plugin_zip,
        plugin_root,
        PLUGIN_FILES,
        license_path,
    )
    _write_archive(
        skill_zip,
        skill_root,
        SKILL_FILES,
        license_path,
    )
    shutil.copyfile(plugin_zip, plugin_alias)
    shutil.copyfile(skill_zip, skill_alias)

    archives = [plugin_zip, plugin_alias, skill_zip, skill_alias]
    errors = [error for archive in archives for error in validate_archive(archive)]
    if errors:
        raise RuntimeError("\n".join(errors))

    return archives


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="构建 ANP 发布压缩包。")
    parser.add_argument("--version", default="0.1.0", help="发布包版本号")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="输出目录，默认使用仓库 dist/",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        archives = package_release(dist_dir=args.dist_dir, version=args.version)
    except (FileNotFoundError, RuntimeError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for archive in archives:
        print(f"已生成: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
