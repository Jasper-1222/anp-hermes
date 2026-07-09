"""anp-client skill 调用真实 Hermes ANP 服务智能体的 E2E。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest


async def run_cli_async(args: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    """运行 anp-client CLI，避免阻塞 pytest event loop 中的 DID/mock 服务。"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@pytest.mark.asyncio
async def test_anp_client_skill_discovers_and_chats_with_hermes(
    hermes_gateway,
    anp_caller_identity,
):
    """anp-client CLI 应能发现服务智能体并通过 chat 获得回复。"""
    repo_root = Path(__file__).resolve().parents[4]
    client_script = repo_root / "clients" / "anp-client" / "scripts" / "anp_client.py"
    endpoint = hermes_gateway["endpoint"]
    client_home = Path(anp_caller_identity["did_path"]).parent
    env = dict(os.environ, ANP_CLIENT_HOME=str(client_home))

    discover_returncode, discover_stdout, discover_stderr = await run_cli_async(
        [str(client_script), "discover", "--endpoint", endpoint, "--json"],
        env=env,
    )
    assert discover_returncode == 0, discover_stderr
    discover_data = json.loads(discover_stdout)
    assert "chat" in discover_data["methods"]
    assert discover_data["service_did"].startswith("did:wba:")

    chat_returncode, chat_stdout, chat_stderr = await run_cli_async(
        [
            str(client_script),
            "chat",
            "--endpoint",
            endpoint,
            "--message",
            "hello-anp-client-skill",
            "--json",
        ],
        env=env,
    )
    assert chat_returncode == 0, chat_stderr
    chat_data = json.loads(chat_stdout)
    assert chat_data["http_status"] == 200
    assert "hello-anp-client-skill" in chat_data["response"]
