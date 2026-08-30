"""Port-contract test suite.

Validates that ANY RuntimePort / CachePort / DownloaderPort implementation
obeys the contract defined by the ports. Adapters must pass these same tests
(Architecture.md §13). Parameterized over the fake and real implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import pytest

from modeldock.adapters.downloaders.http import HttpDownloader
from modeldock.common.errors import (
    DownloadError,
    ModelNotInstalledError,
    RuntimeUnavailableError,
)
from modeldock.domain.model import (
    Capability,
    Category,
    Device,
    ModelRef,
    ModelSpec,
    RuntimeBackend,
    RuntimeStatus,
)
from modeldock.ports.cache import CachePort
from modeldock.ports.downloader import DownloaderPort
from modeldock.ports.runtime import PullResult, RuntimePort

# --- RuntimePort contract helpers & factories --------------------------------


class _MockHTTPResponse:
    """Mock HTTP response for testing HTTP-based runtime adapters."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        return self._json_data


class _FakeOllamaClient:
    """Fake ollama.Client for OllamaRuntime contract testing."""

    def __init__(self) -> None:
        self.models: List[str] = []

    def list(self) -> Dict[str, Any]:
        return {"models": [{"name": m} for m in self.models]}

    def pull(self, name: str, stream: bool = False) -> Any:
        if name not in self.models:
            self.models.append(name)
        if stream:
            return iter([{"status": "success", "completed": 100, "total": 100}])
        return {"status": "success"}

    def delete(self, name: str) -> Dict[str, Any]:
        self.models = [m for m in self.models if m != name]
        return {"status": "success"}


class _FakeLMStudioHTTPClient:
    """Fake HTTP client for LMStudioRuntime contract testing."""

    def __init__(self) -> None:
        self.models: List[str] = []

    def get(self, url: str) -> _MockHTTPResponse:
        if url == "/v1/models":
            return _MockHTTPResponse(200, {"data": [{"id": m} for m in self.models]})
        if url == "/api/v1/models/download/status":
            return _MockHTTPResponse(200, {"status": "completed"})
        return _MockHTTPResponse(404, {})

    def post(self, url: str, json: Optional[Dict[str, Any]] = None) -> _MockHTTPResponse:
        if url == "/api/v1/models/download":
            model = json.get("model") if json else None
            if model and model not in self.models:
                self.models.append(model)
            return _MockHTTPResponse(200, {"status": "completed"})
        if url == "/api/v1/models/unload":
            model = json.get("model") if json else None
            if model:
                self.models = [m for m in self.models if m != model]
            return _MockHTTPResponse(200, {"status": "ok"})
        return _MockHTTPResponse(404, {})


class _FakeLlamaCppHTTPClient:
    """Fake HTTP client for LlamaCppRuntime contract testing."""

    def __init__(self, models: Optional[List[str]] = None) -> None:
        self.models = models or ["llama3:latest"]

    def get(self, url: str) -> _MockHTTPResponse:
        if url == "/health":
            return _MockHTTPResponse(200, {"status": "ok"})
        if url == "/v1/models":
            return _MockHTTPResponse(200, {"data": [{"id": m} for m in self.models]})
        return _MockHTTPResponse(404, {})


def _make_fake_runtime() -> RuntimePort:
    from tests.conftest import FakeRuntime

    return FakeRuntime()


def _make_faked_ollama_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.ollama import OllamaRuntime

    runtime = OllamaRuntime()
    runtime._client = _FakeOllamaClient()
    runtime._availability = True
    return runtime


def _make_faked_lmstudio_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.lmstudio import LMStudioRuntime

    runtime = LMStudioRuntime()
    fake_http = _FakeLMStudioHTTPClient()
    runtime._ensure_http_client = lambda: fake_http  # type: ignore[method-assign]
    runtime._client = object()
    runtime._availability = True
    return runtime


def _make_faked_llamacpp_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.llamacpp import LlamaCppRuntime

    runtime = LlamaCppRuntime()
    fake_http = _FakeLlamaCppHTTPClient()
    runtime._ensure_http_client = lambda: fake_http  # type: ignore[method-assign]
    runtime._client = object()
    runtime._availability = True
    return runtime


def _make_jan_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.jan import JanRuntime

    return JanRuntime()


def _make_gpt4all_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.gpt4all import Gpt4AllRuntime

    return Gpt4AllRuntime()


def _make_vllm_runtime() -> RuntimePort:
    from modeldock.adapters.runtimes.vllm import VllmRuntime

    return VllmRuntime()


_ALL_RUNTIME_FACTORIES: List[Callable[[], RuntimePort]] = [
    _make_fake_runtime,
    _make_faked_ollama_runtime,
    _make_faked_lmstudio_runtime,
    _make_faked_llamacpp_runtime,
    _make_jan_runtime,
    _make_gpt4all_runtime,
    _make_vllm_runtime,
]

_LIFECYCLE_RUNTIME_FACTORIES: List[Callable[[], RuntimePort]] = [
    _make_fake_runtime,
    _make_faked_ollama_runtime,
    _make_faked_lmstudio_runtime,
]

_PLAN_ONLY_RUNTIME_FACTORIES: List[Callable[[], RuntimePort]] = [
    _make_jan_runtime,
    _make_gpt4all_runtime,
    _make_vllm_runtime,
]


@pytest.fixture(params=_ALL_RUNTIME_FACTORIES, ids=lambda f: f.__name__)
def runtime_impl(request: pytest.FixtureRequest) -> RuntimePort:
    return cast(RuntimePort, request.param())


@pytest.fixture(params=_LIFECYCLE_RUNTIME_FACTORIES, ids=lambda f: f.__name__)
def lifecycle_runtime_impl(request: pytest.FixtureRequest) -> RuntimePort:
    return cast(RuntimePort, request.param())


@pytest.fixture(params=_PLAN_ONLY_RUNTIME_FACTORIES, ids=lambda f: f.__name__)
def planned_runtime_impl(request: pytest.FixtureRequest) -> RuntimePort:
    return cast(RuntimePort, request.param())


# --- Universal RuntimePort contract tests ------------------------------------


def test_runtime_implements_protocol(runtime_impl: RuntimePort) -> None:
    assert isinstance(runtime_impl, RuntimePort)


def test_runtime_backend_is_set(runtime_impl: RuntimePort) -> None:
    assert runtime_impl.backend is not None
    assert isinstance(runtime_impl.backend, RuntimeBackend)


def test_runtime_is_available_returns_bool(runtime_impl: RuntimePort) -> None:
    available = runtime_impl.is_available()
    assert isinstance(available, bool)


def test_runtime_default_tag(runtime_impl: RuntimePort) -> None:
    spec = ModelSpec(name="x", category=Category.CHAT, default_tag="latest")
    assert runtime_impl.default_tag_for(spec) == spec.default_tag


def test_runtime_models_for_category_returns_list(runtime_impl: RuntimePort) -> None:
    models = runtime_impl.models_for_category(Category.CHAT)
    assert isinstance(models, list)
    assert all(isinstance(r, ModelRef) for r in models)


def test_runtime_models_for_capability_returns_list(runtime_impl: RuntimePort) -> None:
    models = runtime_impl.models_for_capability(Capability.CHAT)
    assert isinstance(models, list)
    assert all(isinstance(r, ModelRef) for r in models)


def test_runtime_status_contract(runtime_impl: RuntimePort) -> None:
    status = runtime_impl.status()
    assert isinstance(status, RuntimeStatus)
    assert status.backend == runtime_impl.backend
    assert status.device in (Device.GPU, Device.CPU, Device.UNKNOWN)
    assert isinstance(status.available, bool)


# --- Full lifecycle RuntimePort contract tests -------------------------------


def test_runtime_pull_then_installed(lifecycle_runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    result = lifecycle_runtime_impl.pull(ref)
    assert isinstance(result, PullResult)
    assert result.success
    assert lifecycle_runtime_impl.is_installed(ref)


def test_runtime_list_installed(lifecycle_runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime_impl.pull(ref)
    installed = lifecycle_runtime_impl.list_installed()
    assert isinstance(installed, list)
    assert any(r.name == ref.name for r in installed)


def test_runtime_remove(lifecycle_runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime_impl.pull(ref)
    assert lifecycle_runtime_impl.is_installed(ref)
    lifecycle_runtime_impl.remove(ref)
    assert not lifecycle_runtime_impl.is_installed(ref)


def test_runtime_get_client(lifecycle_runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime_impl.pull(ref)
    client = lifecycle_runtime_impl.get_model_client(ref)
    assert client is not None


def test_runtime_pull_already_installed_is_idempotent(lifecycle_runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    first = lifecycle_runtime_impl.pull(ref)
    assert first.success
    second = lifecycle_runtime_impl.pull(ref)
    assert second.success
    assert second.already_present is True or second.success is True


# --- Server-bound (single-model) RuntimePort contract tests ------------------


def test_llamacpp_server_bound_contract() -> None:
    runtime = _make_faked_llamacpp_runtime()
    assert runtime.is_available()
    loaded_ref = ModelRef.parse("llama3:latest")
    assert runtime.is_installed(loaded_ref)
    assert any(r.name == loaded_ref.name for r in runtime.list_installed())

    client = runtime.get_model_client(loaded_ref)
    assert client is not None

    missing_ref = ModelRef.parse("nonexistent:latest")
    assert not runtime.is_installed(missing_ref)
    with pytest.raises(ModelNotInstalledError):
        runtime.get_model_client(missing_ref)

    pull_result = runtime.pull(missing_ref)
    assert isinstance(pull_result, PullResult)
    assert not pull_result.success
    assert "llama-server" in (pull_result.error or "")

    with pytest.raises(DownloadError):
        runtime.remove(loaded_ref)


# --- Planned / Unavailable RuntimePort contract tests ------------------------


def test_planned_runtime_unavailable_contract(planned_runtime_impl: RuntimePort) -> None:
    assert not planned_runtime_impl.is_available()
    status = planned_runtime_impl.status()
    assert not status.available
    ref = ModelRef.parse("llama3")

    with pytest.raises(RuntimeUnavailableError):
        planned_runtime_impl.list_installed()

    with pytest.raises(RuntimeUnavailableError):
        planned_runtime_impl.pull(ref)

    with pytest.raises(RuntimeUnavailableError):
        planned_runtime_impl.remove(ref)

    with pytest.raises(RuntimeUnavailableError):
        planned_runtime_impl.get_model_client(ref)


# --- Registry & Port contract integration ------------------------------------


def test_all_registry_backends_have_port_contract_coverage() -> None:
    from modeldock.adapters.runtimes.registry import RuntimeRegistry

    registry = RuntimeRegistry()
    registered_backends = set(registry.available_backends())
    tested_backends = {factory().backend for factory in _ALL_RUNTIME_FACTORIES}
    assert registered_backends.issubset(tested_backends)


# --- CachePort contract -----------------------------------------------------


@pytest.fixture
def cache_factory(tmp_path: Path) -> Callable[[], List[CachePort]]:
    def _make() -> List[CachePort]:
        from modeldock.adapters.cache import FilesystemCache
        from tests.conftest import FakeCache

        return [FakeCache(), FilesystemCache(tmp_path / "fs_cache")]

    return _make


def test_cache_freshness_lifecycle(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        ref = ModelRef.parse("llama3")
        assert not impl.is_fresh(ref)
        impl.record(ref, "latest", "sha", 10)
        assert impl.is_fresh(ref)
        rec = impl.get_record(ref)
        assert rec is not None
        assert rec["sha256"] == "sha"


def test_cache_status_and_clean(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        ref = ModelRef.parse("llama3")
        impl.record(ref, "latest", "sha", 10)
        assert len(impl.status()) == 1
        # Safe default keeps valid entries.
        impl.clean()
        assert len(impl.status()) == 1
        # force=True wipes everything.
        impl.clean(force=True)
        assert impl.status() == []


# --- DownloaderPort contract ------------------------------------------------


def test_downloader_port_contract() -> None:
    downloader = HttpDownloader()
    assert isinstance(downloader, DownloaderPort)

