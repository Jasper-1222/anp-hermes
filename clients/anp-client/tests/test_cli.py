"""anp-client CLI 基础命令测试。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from did_identity import load_or_create_identity
from did_server import did_document_route, format_url_host, is_loopback_host

CLIENT_ROOT = Path(__file__).resolve().parents[1]
CLI = CLIENT_ROOT / "scripts" / "anp_client.py"


def run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_did_document_route(client_home: Path) -> None:
    identity = load_or_create_identity(client_home)
    route = did_document_route(identity.did)

    assert route.startswith("/agent/e1_")
    assert route.endswith("/did.json")


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_is_loopback_host_accepts_loopback(host: str) -> None:
    assert is_loopback_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.2", "example.com"])
def test_is_loopback_host_rejects_non_loopback(host: str) -> None:
    assert not is_loopback_host(host)


def test_format_url_host_wraps_ipv6_loopback() -> None:
    assert format_url_host("::1") == "[::1]"
    assert format_url_host("127.0.0.1") == "127.0.0.1"


def test_serve_did_check_only_accepts_ipv6_loopback(client_home: Path) -> None:
    env = {**os.environ, "ANP_CLIENT_HOME": str(client_home), "ANP_DID_SERVER_HOST": "::1"}
    result = run_cli(["serve-did", "--check-only"], env=env)

    assert result.returncode == 0
    assert "serve-did 配置检查通过" in result.stdout


def test_whoami_creates_identity(client_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = {**os.environ, "ANP_CLIENT_HOME": str(client_home)}
    result = run_cli(["whoami"], env=env)

    assert result.returncode == 0
    assert "个人智能体 DID:" in result.stdout
    assert str(client_home) in result.stdout
    assert (client_home / "did.json").exists()
    assert (client_home / "private_key.pem").exists()


def test_serve_did_rejects_non_loopback(client_home: Path) -> None:
    env = {**os.environ, "ANP_CLIENT_HOME": str(client_home), "ANP_DID_SERVER_HOST": "0.0.0.0"}
    result = run_cli(["serve-did", "--check-only"], env=env)

    assert result.returncode == 2
    assert "仅支持 loopback" in result.stderr
