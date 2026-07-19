"""Unit tests for the top-level ``modeldock`` SDK API surface.

Offline commands (list/search/info/categories/recommend/cache) are exercised
against the real bundled registry. Runtime-dependent commands (install/remove/
verify/load) are exercised via an explicit ``Manager`` wired with fakes, since
the lazy singleton builds a real runtime. See Architecture.md S5.
"""

from __future__ import annotations

import pytest

import modeldock as md
from modeldock.common.errors import ModelNotFoundError
from modeldock.domain.model import RuntimeBackend


def test_version_exported() -> None:
    assert md.__version__


def test_list_offline() -> None:
    models = md.list()
    assert len(models) >= 1
    assert any(m.name == "llama3" for m in models)


def test_search_offline() -> None:
    hits = md.search("llama")
    assert hits
    assert any(m.name == "llama3" for m in hits)


def test_info_offline() -> None:
    spec = md.info("llama3")
    assert spec.name == "llama3"


def test_info_unknown_raises() -> None:
    with pytest.raises(ModelNotFoundError):
        md.info("ghost-model")


def test_info_returns_modelinfo_with_installed_fields() -> None:
    from modeldock.domain.model import ModelInfo

    info = md.info("llama3")
    assert isinstance(info, ModelInfo)
    assert info.name == "llama3"
    # installed flag must be consistent with the installed tags, regardless of
    # what is actually installed in the test environment.
    assert info.installed is bool(info.installed_tags)


def test_categories_offline() -> None:
    cats = md.categories()
    assert md.Category.CHAT in cats


def test_recommend_offline() -> None:
    recs = md.recommend("coding")
    assert recs


def test_cache_status_offline() -> None:
    assert isinstance(md.cache.status(), list)


def test_cache_clean_offline() -> None:
    assert isinstance(md.cache.clean(), list)


def test_configure_builds_singleton() -> None:
    md.configure(auto_install=True, log_level="INFO")
    mgr = md._manager()
    assert mgr._config.settings.auto_install is True
    assert mgr._config.settings.log_level == "INFO"


def test_manager_factory_constructs() -> None:
    mgr = md.Manager(backend="ollama", auto_install=False)
    assert mgr._backend == RuntimeBackend.OLLAMA


def test_sdk_install_via_fake_manager() -> None:
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    runtime = FakeRuntime()
    registry = FakeRegistry()
    cache = FakeCache()
    mgr = md.ModelManager(runtime=runtime, registry=registry, cache=cache)
    ref = mgr.install("llama3")
    assert ref.name == "llama3"
    assert mgr.verify("llama3")


def test_sdk_remove_via_fake_manager() -> None:
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    runtime = FakeRuntime()
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    mgr.install("llama3")
    mgr.remove("llama3")
    assert not mgr.verify("llama3")


def test_sdk_load_via_fake_manager() -> None:
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    runtime = FakeRuntime()
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    client = mgr.load("llama3", auto_install=True)
    assert client == {"client": "llama3:latest"}


def test_info_falls_back_for_installed_uncatalogued_model() -> None:
    from modeldock.domain.model import ModelRef
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    ref = ModelRef.parse("localmodel:latest")
    runtime = FakeRuntime(installed=[ref])
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    info = mgr.info("localmodel:latest")
    assert info.name == "localmodel"
    assert info.installed is True
    assert info.installed_tags == ["latest"]


def test_info_unknown_not_installed_still_raises() -> None:
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    runtime = FakeRuntime(installed=[])
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    with pytest.raises(ModelNotFoundError):
        mgr.info("ghost-model")


def test_load_falls_back_for_installed_uncatalogued_model() -> None:
    from modeldock.domain.model import ModelRef
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    ref = ModelRef.parse("localmodel:latest")
    runtime = FakeRuntime(installed=[ref])
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    client = mgr.load("localmodel:latest")
    assert client == {"client": "localmodel:latest"}


def test_install_falls_back_for_installed_uncatalogued_model() -> None:
    from modeldock.domain.model import ModelRef
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    ref = ModelRef.parse("localmodel:latest")
    runtime = FakeRuntime(installed=[ref])
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    result = mgr.install("localmodel:latest")
    assert result.name == "localmodel"


def test_modelref_and_backend_exports() -> None:
    assert md.ModelRef.parse("llama3:8b").qualified_name() == "llama3:8b"
    assert md.RuntimeBackend.from_value("ollama") == RuntimeBackend.OLLAMA


def test_sdk_run_via_fake_manager() -> None:
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    runtime = FakeRuntime()
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    result = mgr.run("llama3", prompt="hi")
    assert result.success is True


def test_sdk_run_exported() -> None:
    assert hasattr(md, "run")
    assert "run" in md.__all__


def test_load_routes_backend_to_manager() -> None:
    from modeldock.domain.model import RuntimeBackend

    # Manager(backend=...) sets the active backend without touching a runtime.
    mgr = md.Manager(backend="ollama")
    assert mgr._backend == RuntimeBackend.OLLAMA


def test_info_surfaces_installed_tags_for_catalog_model() -> None:
    from modeldock.domain.model import ModelRef
    from tests.conftest import FakeCache, FakeRegistry, FakeRuntime

    ref = ModelRef.parse("llama3:latest")
    runtime = FakeRuntime(installed=[ref])
    mgr = md.ModelManager(runtime=runtime, registry=FakeRegistry(), cache=FakeCache())
    info = mgr.info("llama3")
    assert info.installed is True
    assert info.installed_tags == ["latest"]
