import pytest
import yaml

from . import conftest as e2e_conftest


@pytest.mark.asyncio
async def test_did_document_server_hosts_document(did_document_server, anp_caller_identity):
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(did_document_server.document_url) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["id"] == anp_caller_identity["did"]


@pytest.mark.asyncio
async def test_mock_echo_gateway_uses_generated_config_without_user_config(
    tmp_path,
    did_document_server,
    mock_llm_server,
    monkeypatch,
):
    """Echo E2E 使用生成配置和临时 HOME，不读取用户真实配置。"""
    captured = {}

    class DummyProcess:
        def terminate(self):
            captured["terminated"] = True

        def wait(self, timeout=None):
            captured["wait_timeout"] = timeout
            return 0

        def kill(self):
            captured["killed"] = True

    def fail_if_user_config_is_read():
        raise AssertionError("Echo E2E 不应读取用户真实 Hermes config")

    def fake_popen(args, env, stdout, stderr):
        captured["args"] = args
        captured["env"] = env
        return DummyProcess()

    monkeypatch.setattr(e2e_conftest, "_load_user_hermes_config", fail_if_user_config_is_read)
    monkeypatch.setattr(e2e_conftest, "free_port", lambda: 12345)
    monkeypatch.setattr(e2e_conftest, "wait_for_url", lambda url, timeout=60.0: True)
    monkeypatch.setattr(e2e_conftest.subprocess, "Popen", fake_popen)

    gateway = e2e_conftest._start_hermes_gateway(
        tmp_path,
        did_document_server,
        use_mock_llm=True,
        mock_llm_server=mock_llm_server,
        install_echo_skill=True,
    )
    try:
        hermes_home = gateway["home"]
        config = yaml.safe_load((hermes_home / "config.yaml").read_text(encoding="utf-8"))

        assert config["model"] == {"default": "anp-echo-model", "provider": "anp-e2e"}
        assert config["providers"]["anp-e2e"]["api"] == f"{mock_llm_server.base_url}/v1"
        assert config["gateway"]["platforms"]["anp"]["extra"]["data_dir"] == str(
            hermes_home / "anp-agent-data"
        )

        env = captured["env"]
        assert env["HERMES_HOME"] == str(hermes_home)
        assert env["HOME"] == str(hermes_home / "home")
        assert env["ANP_ALLOW_ALL_USERS"] == "1"
        assert env["ANP_DID_RESOLVER_BASE_URL"] == did_document_server.base_url
        assert env["ANP_E2E_API_KEY"] == "test"
        assert env["ANP_HOME_CHANNEL"] == "none"
    finally:
        e2e_conftest._stop_hermes_gateway(gateway)


def test_llm_prerequisites_skip_without_slow_flag_before_reading_user_config(monkeypatch):
    """未传 --run-slow-e2e 时应在读取用户配置前跳过。"""

    class DummyConfig:
        def getoption(self, name):
            assert name == "--run-slow-e2e"
            return False

    def fail_if_user_config_is_read():
        raise AssertionError("未传 --run-slow-e2e 时不应读取用户真实 Hermes config")

    monkeypatch.setattr(e2e_conftest, "_load_user_hermes_config", fail_if_user_config_is_read)

    with pytest.raises(pytest.skip.Exception, match="--run-slow-e2e"):
        e2e_conftest._validate_llm_e2e_prerequisites(DummyConfig())


def test_llm_prerequisites_skip_without_provider_api_key(monkeypatch):
    """缺少 provider API key 时应给出明确 skip reason。"""

    class DummyConfig:
        def getoption(self, name):
            assert name == "--run-slow-e2e"
            return True

    monkeypatch.setattr(
        e2e_conftest,
        "_load_user_hermes_config",
        lambda: {"model": {"provider": "kimi"}},
    )
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("ANP_E2E_LLM_KEY_ENV", raising=False)

    with pytest.raises(pytest.skip.Exception, match="KIMI_API_KEY"):
        e2e_conftest._validate_llm_e2e_prerequisites(DummyConfig())
