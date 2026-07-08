"""E2E 测试共享配置与 fixtures。"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
import requests
import yaml
from anp.authentication import create_did_wba_document

from tests.helpers.did_server import DIDDocumentServer
from tests.helpers.mock_llm import MockLLMServer


def pytest_addoption(parser):
    """注册 E2E 测试选项。"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="运行 E2E 测试（需要本地 Hermes 安装）",
    )
    parser.addoption(
        "--run-slow-e2e",
        action="store_true",
        default=False,
        help="运行需要真实 LLM 的慢速 E2E 测试",
    )


def pytest_collection_modifyitems(config, items):
    """未传 --run-e2e 时跳过 e2e 目录下所有测试。"""
    if config.getoption("--run-e2e"):
        return
    skip = pytest.mark.skip(reason="需要 --run-e2e 选项才能运行 E2E 测试")
    e2e_root = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(e2e_root):
            item.add_marker(skip)


def free_port() -> int:
    """申请一个本地空闲 TCP 端口。

    设置 SO_REUSEADDR，使后续服务进程在端口处于 TIME_WAIT 时仍能绑定，
    从而降低端口不可用导致的启动失败概率；但无法完全消除 TOCTOU 竞争。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_url(url: str, timeout: float = 60.0, interval: float = 0.5) -> bool:
    """轮询等待 URL 返回 HTTP 200。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    return False


def _load_user_hermes_config() -> dict[str, Any]:
    """读取用户真实 ~/.hermes/config.yaml 的 model/provider 配置。

    如果文件不存在或解析失败，返回空字典。
    """
    config_path = Path.home() / ".hermes" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


@pytest.fixture
def anp_caller_identity(tmp_path: Path) -> dict[str, Any]:
    """动态生成 ANP caller DID WBA 身份及密钥文件。"""
    workdir = tmp_path / "caller"
    workdir.mkdir(parents=True, exist_ok=True)

    did_document, keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    did = did_document["id"]
    auth_key = keys.get("key-1")
    assert auth_key is not None, "DID 文档未生成 key-1 认证密钥"
    private_key_pem = auth_key[0]

    did_path = workdir / "did.json"
    key_path = workdir / "private_key.pem"
    did_path.write_text(json.dumps(did_document), encoding="utf-8")
    key_path.write_bytes(private_key_pem)

    return {
        "did": did,
        "did_document": did_document,
        "private_key_pem": private_key_pem,
        "did_path": did_path,
        "key_path": key_path,
    }


@pytest_asyncio.fixture
async def did_document_server(anp_caller_identity: dict[str, Any]) -> DIDDocumentServer:
    """启动本地 DID 文档服务器，供 ANP verifier 解析 caller DID。"""
    async with DIDDocumentServer(anp_caller_identity["did_document"]) as server:
        yield server


@pytest_asyncio.fixture
async def mock_llm_server() -> MockLLMServer:
    """启动 OpenAI 兼容的 mock LLM 服务器，用于阶段一 Echo E2E。"""
    async with MockLLMServer() as server:
        yield server


def _start_hermes_gateway(
    tmp_path: Path,
    did_document_server: DIDDocumentServer,
    *,
    use_mock_llm: bool,
    mock_llm_server: MockLLMServer | None = None,
    install_echo_skill: bool = False,
) -> dict[str, Any]:
    """启动真实 Hermes gateway 的通用实现。"""
    # 1. 准备临时 HERMES_HOME
    hermes_home = tmp_path / "hermes_home"
    hermes_home.mkdir(parents=True, exist_ok=True)
    process_home = hermes_home / "home"
    process_home.mkdir(parents=True, exist_ok=True)
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    skills_dir = hermes_home / "skills"
    skills_dir.mkdir(exist_ok=True)

    # 2. 符号链接 anp-agent 插件
    plugin_src = Path(__file__).resolve().parents[2]
    plugin_link = plugins_dir / "anp-agent"
    plugin_link.symlink_to(plugin_src, target_is_directory=True)

    # 3. 按需安装 anp-echo skill
    if install_echo_skill:
        echo_skill_dst = skills_dir / "anp-echo"
        echo_skill_src = Path(__file__).resolve().parent / "data" / "anp-echo"
        echo_skill_dst.symlink_to(echo_skill_src, target_is_directory=True)

    # 4. 写入 Hermes 配置
    port = free_port()
    if use_mock_llm:
        config: dict[str, Any] = {}
    else:
        user_config = _load_user_hermes_config()
        if not user_config:
            pytest.skip("未找到 ~/.hermes/config.yaml，无法运行 LLM E2E 测试")
        config = dict(user_config)

    config.setdefault("gateway", {})
    config["gateway"]["platforms"] = {
        "anp": {
            "enabled": True,
            "extra": {
                "host": "127.0.0.1",
                "port": port,
                "hostname": "localhost",
                "endpoint": f"http://127.0.0.1:{port}",
                "data_dir": str(hermes_home / "anp-agent-data"),
                "request_timeout": 60,
                "future_ttl": 120,
            },
        }
    }
    config.setdefault("plugins", {})
    config["plugins"]["enabled"] = list(
        set(config.get("plugins", {}).get("enabled", []) + ["anp-agent"])
    )
    config["skills"] = {"external_dirs": [], "template_vars": True, "inline_shell": False}

    # 支持通过环境变量覆盖真实 LLM provider（用于一次性 E2E 验证）
    override_provider = os.environ.get("ANP_E2E_LLM_PROVIDER", "")
    override_api = os.environ.get("ANP_E2E_LLM_API", "")
    override_key_env = os.environ.get("ANP_E2E_LLM_KEY_ENV", "")

    if use_mock_llm:
        if mock_llm_server is None:
            raise ValueError("使用 mock LLM 时必须传入 mock_llm_server")
        mock_base_url = mock_llm_server.base_url
        config["model"] = {
            "default": "anp-echo-model",
            "provider": "anp-e2e",
        }
        config["providers"] = {
            "anp-e2e": {
                "name": "anp-e2e",
                "api": f"{mock_base_url}/v1",
                "transport": "openai_chat",
                "key_env": "ANP_E2E_API_KEY",
            }
        }
    elif override_provider and override_api and override_key_env:
        # 允许一次性覆盖真实 LLM provider，不修改用户配置文件
        config["model"] = {
            "default": override_provider,
            "provider": override_provider,
        }
        config["providers"] = {
            override_provider: {
                "name": override_provider,
                "api": override_api,
                "transport": "openai_chat",
                "key_env": override_key_env,
            }
        }

    config_path = hermes_home / "config.yaml"
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)

    # 5. 启动 hermes gateway run 子进程
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["HOME"] = str(hermes_home / "home")
    env["ANP_ALLOW_ALL_USERS"] = "1"
    env["ANP_DID_RESOLVER_BASE_URL"] = did_document_server.base_url
    if use_mock_llm:
        env["ANP_E2E_API_KEY"] = "test"
    # 设置一个非 anp: 前缀的 home channel，避免 Hermes 发送 home channel 提示
    # 该提示会抢先在 LLM 回复前写入 RPC Future，导致真实回复被丢弃。
    env["ANP_HOME_CHANNEL"] = "none"

    # 启动 gateway，日志写入临时目录便于失败诊断
    gateway_log = hermes_home / "gateway.log"
    log_file = open(gateway_log, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            ["hermes", "gateway", "run", "--accept-hooks"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=log_file,
        )
    except Exception:
        log_file.close()
        raise

    endpoint = f"http://127.0.0.1:{port}"
    try:
        if not wait_for_url(f"{endpoint}/agent/ad.json", timeout=60.0):
            proc.terminate()
            try:
                proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            pytest.fail(f"Hermes gateway 未能在 60 秒内启动，endpoint={endpoint}")
        return {"endpoint": endpoint, "process": proc, "home": hermes_home, "_log_file": log_file}
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
        raise


def _stop_hermes_gateway(gateway: dict[str, Any]) -> None:
    """停止 hermes gateway 子进程并关闭日志文件。"""
    proc = gateway["process"]
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
    except subprocess.TimeoutExpired:
        proc.kill()
    gateway["_log_file"].close()


@pytest.fixture
def hermes_gateway(
    tmp_path: Path,
    did_document_server: DIDDocumentServer,
    mock_llm_server: MockLLMServer,
):
    """启动真实 Hermes gateway，加载 anp-agent 插件与 anp-echo skill。"""
    gateway = _start_hermes_gateway(
        tmp_path,
        did_document_server,
        use_mock_llm=True,
        mock_llm_server=mock_llm_server,
        install_echo_skill=True,
    )
    try:
        yield gateway
    finally:
        _stop_hermes_gateway(gateway)


# 常见 provider 到 API key 环境变量的映射（用于阶段二 LLM E2E 前置检查）
_PROVIDER_API_KEY_ENV = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "alibaba": "DASHSCOPE_API_KEY",
    "groq": "GROQ_API_KEY",
    "xai": "XAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "google": "GOOGLE_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "azure-foundry": "AZURE_ANTHROPIC_KEY",
    "kimi": "KIMI_API_KEY",
}


def _validate_llm_e2e_prerequisites(config) -> dict[str, Any]:
    """检查真实 LLM E2E 前置条件，失败时在启动 gateway 前 skip。"""
    if not config.getoption("--run-slow-e2e"):
        pytest.skip("需要 --run-slow-e2e 选项才能运行 LLM E2E 测试")

    user_config = _load_user_hermes_config()
    model_cfg = user_config.get("model", {})
    provider = model_cfg.get("provider", "")
    if not provider:
        pytest.skip("真实 ~/.hermes/config.yaml 未配置 model.provider，跳过 LLM E2E 测试")

    key_env = _PROVIDER_API_KEY_ENV.get(provider.lower())
    override_key_env = os.environ.get("ANP_E2E_LLM_KEY_ENV", "")
    if override_key_env:
        key_env = override_key_env
    if not key_env or not os.environ.get(key_env):
        pytest.skip(
            f"LLM E2E 测试需要环境变量 {key_env or '对应 API KEY'}（当前 provider={provider}），未设置则跳过"
        )

    return user_config


@pytest.fixture
def llm_hermes_gateway(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    did_document_server: DIDDocumentServer,
):
    """启动真实 Hermes gateway，使用真实 LLM provider（阶段二）。"""
    _validate_llm_e2e_prerequisites(request.config)

    gateway = _start_hermes_gateway(
        tmp_path,
        did_document_server,
        use_mock_llm=False,
    )
    try:
        yield gateway
    finally:
        _stop_hermes_gateway(gateway)
