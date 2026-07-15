"""插件包化与发布结构测试。"""

import importlib
import importlib.util
import sys
import zipfile
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
PACKAGER_PATH = REPO_ROOT / "scripts" / "package_anp_release.py"
RUNTIME_MODULES = [
    "adapter",
    "auth",
    "bridge",
    "config",
    "constants",
    "identity",
    "server",
]
FORBIDDEN_ZIP_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
FORBIDDEN_ZIP_NAMES = {
    ".coverage",
    "did.json",
}


def _load_packager():
    spec = importlib.util.spec_from_file_location("plugin_test_packager", PACKAGER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_gateway_mocks() -> None:
    """提供导入 ANPAdapter 所需的最小 Hermes gateway 模块。"""
    if "gateway.platforms.base" not in sys.modules:
        base_module = ModuleType("gateway.platforms.base")

        class BasePlatformAdapter:
            def __init__(self, config, platform=None):
                self.config = config
                self.platform = platform

        class SendResult:
            def __init__(self, success, message_id=None, error=None, **kwargs):
                self.success = success
                self.message_id = message_id
                self.error = error
                for key, value in kwargs.items():
                    setattr(self, key, value)

        base_module.BasePlatformAdapter = BasePlatformAdapter
        base_module.SendResult = SendResult
        sys.modules["gateway.platforms.base"] = base_module

    if "gateway.config" not in sys.modules:
        config_module = ModuleType("gateway.config")

        class Platform:
            def __init__(self, name):
                self.name = name

            @property
            def value(self):
                return self.name

        config_module.Platform = Platform
        sys.modules["gateway.config"] = config_module


def test_runtime_modules_import_from_anp_agent_package():
    """运行时代码应通过唯一包名 anp_agent 导入。"""
    _ensure_gateway_mocks()
    for module_name in RUNTIME_MODULES:
        module = importlib.import_module(f"anp_agent.{module_name}")
        assert module.__name__ == f"anp_agent.{module_name}"


def _load_plugin_entrypoint_like_hermes(
    module_name: str = "hermes_plugins.anp_agent",
) -> ModuleType:
    """按 Hermes 目录插件 loader 的方式加载根 entrypoint。"""
    parent_name = module_name.rsplit(".", 1)[0]
    if parent_name not in sys.modules:
        parent_module = ModuleType(parent_name)
        parent_module.__path__ = []
        sys.modules[parent_name] = parent_module

    init_file = PLUGIN_ROOT / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        module_name,
        init_file,
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = module_name
    module.__path__ = [str(PLUGIN_ROOT)]
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def test_entrypoint_registers_platform_with_packaged_adapter():
    """根 entrypoint 在 Hermes package 加载语境下仍应注册 anp 平台。"""
    _ensure_gateway_mocks()
    module = _load_plugin_entrypoint_like_hermes(
        "hermes_plugins.anp_agent_test_register"
    )
    ctx = Mock()

    module.register(ctx)

    ctx.register_platform.assert_called_once()
    kwargs = ctx.register_platform.call_args.kwargs
    assert kwargs["name"] == "anp"
    adapter = kwargs["adapter_factory"]({})
    assert (
        adapter.__class__.__module__
        == "hermes_plugins.anp_agent_test_register.anp_agent.adapter"
    )


def test_entrypoint_does_not_insert_plugin_root_into_sys_path():
    """加载 entrypoint 不应污染全局 sys.path。"""
    plugin_root = str(PLUGIN_ROOT)
    original_path = list(sys.path)
    sys.path[:] = [path for path in sys.path if path != plugin_root]
    try:
        _load_plugin_entrypoint_like_hermes("hermes_plugins.anp_agent_test_no_syspath")
        assert plugin_root not in sys.path
    finally:
        sys.path[:] = original_path


def test_release_zip_contains_packaged_plugin_root_only(tmp_path: Path):
    """干净 clone 中临时构建的稳定插件包结构正确。"""
    packager = _load_packager()
    packager.package_release(root=REPO_ROOT, dist_dir=tmp_path, version="9.9.9")
    zip_path = tmp_path / "anp-agent.zip"

    with zipfile.ZipFile(zip_path) as archive:
        names = [name.rstrip("/") for name in archive.namelist()]

    assert "plugin.yaml" in names
    assert "__init__.py" in names
    assert "README.md" in names
    assert "pyproject.toml" in names
    assert "LICENSE" in names
    assert any(name == "anp_agent" or name.startswith("anp_agent/") for name in names)

    for name in names:
        path = Path(name)
        assert not any(part in FORBIDDEN_ZIP_PARTS for part in path.parts)
        assert path.name not in FORBIDDEN_ZIP_NAMES
        assert not path.name.endswith(".pem")
        assert ".bak." not in path.name
