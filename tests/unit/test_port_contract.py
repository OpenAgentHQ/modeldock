"""Port-contract test suite.

Validates that ANY RuntimePort / CachePort / DownloaderPort implementation
obeys the contract defined by the ports (Architecture.md S13). Adapters must
pass these same tests, and every backend registered in RuntimeRegistry must
have coverage here — see ``test_registry_backend_coverage`` below.

The suite is split into four groups because adapters fall into genuinely
different behavioral categories and a single parametrization would either
under-test the capable adapters or force fake behavior onto the ones that
correctly refuse:

* universal   -- properties every RuntimePort implementation must satisfy
                 regardless of what it actually supports (backend identity,
                 status(), default_tag_for(), category/capability lookups).
* lifecycle   -- adapters that can actually pull/install/remove models
                 in-process (FakeRuntime, OllamaRuntime, LMStudioRuntime),
                 exercised with fake/mocked clients so no real daemon is
                 required.
* server-bound -- LlamaCppRuntime, which binds exactly one GGUF model per
                 server process and must fail informatively rather than
                 silently for pull/remove.
* planned      -- JanRuntime, Gpt4AllRuntime, VllmRuntime, which are not
                 shipped yet and must consistently raise
                 RuntimeUnavailableError rather than doing something
                 undefined.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List

import pytest

from modeldock.adapters.runtimes.gpt4all import Gpt4AllRuntime
from modeldock.adapters.runtimes.jan import JanRuntime
from modeldock.adapters.runtimes.llamacpp import LlamaCppRuntime
from modeldock.adapters.runtimes.lmstudio import LMStudioRuntime
from modeldock.adapters.runtimes.ollama import OllamaRuntime
from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.adapters.runtimes.vllm import VllmRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import Category, ModelRef, ModelSpec, RuntimeBackend
from modeldock.ports.cache import CachePort
from modeldock.ports.downloader import DownloaderPort
from modeldock.ports.runtime import PullResult, RuntimePort, RuntimeStatus
from tests.conftest import FakeCache, FakeRuntime

# =============================================================================
# Universal RuntimePort contract — every adapter, regardless of capability.
# =============================================================================


def _all_runtime_implementations() -> List[RuntimePort]:
    """One instance of every adapter registered for a RuntimeBackend.

    Kept in sync with ``RuntimeRegistry`` by ``test_registry_backend_coverage``
    below, so a new adapter added to the registry without a corresponding
    entry here fails loudly instead of silently going untested.
    """
    return [
        FakeRuntime(),
        OllamaRuntime(),
        LMStudioRuntime(),
        LlamaCppRuntime(),
        JanRuntime(),
        Gpt4AllRuntime(),
        VllmRuntime(),
    ]


@pytest.fixture(params=_all_runtime_implementations(), ids=lambda impl: type(impl).__name__)
def any_runtime(request: pytest.FixtureRequest) -> RuntimePort:
    return request.param


def test_runtime_conforms_to_protocol(any_runtime: RuntimePort) -> None:
    assert isinstance(any_runtime, RuntimePort)


def test_runtime_backend_is_set(any_runtime: RuntimePort) -> None:
    assert any_runtime.backend is not None
    assert isinstance(any_runtime.backend, RuntimeBackend)


def test_runtime_is_available_returns_bool(any_runtime: RuntimePort) -> None:
    assert isinstance(any_runtime.is_available(), bool)


def test_runtime_default_tag(any_runtime: RuntimePort) -> None:
    spec = ModelSpec(name="x", category=Category.CHAT)
    assert any_runtime.default_tag_for(spec) == spec.default_tag


def test_runtime_status_contract(any_runtime: RuntimePort) -> None:
    status = any_runtime.status()
    assert isinstance(status, RuntimeStatus)
    assert status.backend is not None
    assert status.device.value in {"gpu", "cpu", "unknown"}
    # An unavailable runtime can never report a detected device.
    if not status.available:
        assert status.device.value == "unknown"


def test_runtime_models_for_category_returns_list(any_runtime: RuntimePort) -> None:
    result = any_runtime.models_for_category(Category.CHAT)
    assert isinstance(result, list)
    assert all(isinstance(ref, ModelRef) for ref in result)


def test_runtime_models_for_capability_returns_list(any_runtime: RuntimePort) -> None:
    from modeldock.domain.model import Capability

    result = any_runtime.models_for_capability(Capability.CHAT)
    assert isinstance(result, list)


# =============================================================================
# Lifecycle contract — adapters that can pull/install/list/remove in-process.
# =============================================================================


def _fake_ollama_runtime() -> OllamaRuntime:
    """OllamaRuntime wired to an in-memory fake ollama.Client."""

    class _FakeOllamaClient:
        def __init__(self) -> None:
            self._models: List[str] = []

        def pull(self, name: str, stream: bool = False) -> Any:
            self._models.append(name)
            if stream:
                return iter([{"status": "success", "completed": 1, "total": 1}])
            return None

        def list(self) -> dict:
            return {"models": [{"name": n} for n in self._models]}

        def delete(self, name: str) -> dict:
            self._models = [n for n in self._models if n != name]
            return {"status": "success"}

    runtime = OllamaRuntime()
    runtime._client = _FakeOllamaClient()  # type: ignore[attr-defined]
    runtime._availability = True  # skip the real HTTP probe
    return runtime


def _fake_lmstudio_runtime() -> LMStudioRuntime:
    """LMStudioRuntime wired to fake OpenAI + httpx clients."""

    class _FakeHTTPClient:
        def __init__(self) -> None:
            self._models: List[str] = []

        def get(self, url: str) -> Any:
            class _Resp:
                def __init__(self, status_code: int, data: dict) -> None:
                    self.status_code = status_code
                    self._data = data

                def json(self) -> dict:
                    return self._data

            if url == "/v1/models":
                return _Resp(200, {"data": [{"id": m} for m in self._models]})
            if url == "/api/v1/models/download/status":
                return _Resp(200, {"status": "completed"})
            return _Resp(404, {})

        def post(self, url: str, json: dict | None = None) -> Any:
            class _Resp:
                def __init__(self, status_code: int, data: dict) -> None:
                    self.status_code = status_code
                    self._data = data

                def json(self) -> dict:
                    return self._data

            if url == "/api/v1/models/download":
                model_id = (json or {}).get("model", "")
                self._models.append(model_id)
                return _Resp(200, {"status": "completed"})
            if url == "/api/v1/models/unload":
                model_id = (json or {}).get("model", "")
                self._models = [m for m in self._models if m != model_id]
                return _Resp(200, {"status": "ok"})
            return _Resp(404, {})

    http_client = _FakeHTTPClient()
    runtime = LMStudioRuntime()
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]
    runtime._client = object()  # OpenAI client not exercised by these tests
    runtime._availability = True
    return runtime


_LIFECYCLE_FACTORIES: dict[str, Callable[[], RuntimePort]] = {
    "FakeRuntime": FakeRuntime,
    "OllamaRuntime": _fake_ollama_runtime,
    "LMStudioRuntime": _fake_lmstudio_runtime,
}


@pytest.fixture(params=list(_LIFECYCLE_FACTORIES), ids=list(_LIFECYCLE_FACTORIES))
def lifecycle_runtime(request: pytest.FixtureRequest) -> RuntimePort:
    return _LIFECYCLE_FACTORIES[request.param]()


def test_lifecycle_pull_then_installed(lifecycle_runtime: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    result = lifecycle_runtime.pull(ref)
    assert isinstance(result, PullResult)
    assert result.success
    assert lifecycle_runtime.is_installed(ref)


def test_lifecycle_list_installed(lifecycle_runtime: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime.pull(ref)
    installed = lifecycle_runtime.list_installed()
    # Compare on (name, tag) rather than full ModelRef equality: adapters are
    # free to stamp their own backend onto the returned refs (Ollama/LM
    # Studio do), which is a legitimate implementation detail, not a
    # contract violation.
    assert any(existing.name == ref.name and existing.tag == ref.tag for existing in installed)


def test_lifecycle_pull_is_idempotent(lifecycle_runtime: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    first = lifecycle_runtime.pull(ref)
    second = lifecycle_runtime.pull(ref)
    assert first.success
    assert second.success


def test_lifecycle_remove(lifecycle_runtime: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime.pull(ref)
    lifecycle_runtime.remove(ref)
    assert not lifecycle_runtime.is_installed(ref)


def test_lifecycle_get_client(lifecycle_runtime: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    lifecycle_runtime.pull(ref)
    client = lifecycle_runtime.get_model_client(ref)
    assert client is not None


_REAL_LIFECYCLE_FACTORIES: dict[str, Callable[[], RuntimePort]] = {
    "OllamaRuntime": _fake_ollama_runtime,
    "LMStudioRuntime": _fake_lmstudio_runtime,
}


@pytest.fixture(params=list(_REAL_LIFECYCLE_FACTORIES), ids=list(_REAL_LIFECYCLE_FACTORIES))
def real_lifecycle_runtime(request: pytest.FixtureRequest) -> RuntimePort:
    return _REAL_LIFECYCLE_FACTORIES[request.param]()


def test_lifecycle_get_client_before_install_raises(real_lifecycle_runtime: RuntimePort) -> None:
    """Real adapters must guard get_model_client on install state.

    FakeRuntime is intentionally a minimal test double and does not enforce
    this invariant, so it is excluded here (see FakeRuntime.get_model_client
    in tests/conftest.py) — the guard itself lives in BaseRuntime and is
    covered for every adapter that subclasses it.
    """
    from modeldock.common.errors import ModelNotInstalledError

    ref = ModelRef.parse("not-installed-model")
    with pytest.raises(ModelNotInstalledError):
        real_lifecycle_runtime.get_model_client(ref)


# =============================================================================
# Server-bound contract — LlamaCppRuntime (exactly one model per process).
# =============================================================================


def _fake_llamacpp_runtime(model_id: str | None = None) -> LlamaCppRuntime:
    class _FakeHTTPClient:
        def __init__(self, model_id: str | None) -> None:
            self._model_id = model_id

        def get(self, url: str) -> Any:
            class _Resp:
                def __init__(self, status_code: int, data: dict) -> None:
                    self.status_code = status_code
                    self._data = data

                def json(self) -> dict:
                    return self._data

            if url == "/health":
                return _Resp(200, {"status": "ok"})
            if url == "/v1/models":
                data = {"data": [{"id": self._model_id}]} if self._model_id else {"data": []}
                return _Resp(200, data)
            return _Resp(404, {})

    runtime = LlamaCppRuntime()
    runtime._ensure_http_client = lambda: _FakeHTTPClient(model_id)  # type: ignore[assignment]
    runtime._availability = True
    return runtime


def test_llamacpp_lists_at_most_one_model() -> None:
    runtime = _fake_llamacpp_runtime(model_id="model.gguf")
    installed = runtime.list_installed()
    assert len(installed) <= 1


def test_llamacpp_pull_is_unsupported() -> None:
    runtime = _fake_llamacpp_runtime()
    result = runtime.pull(ModelRef.parse("anything"))
    assert not result.success
    assert result.error is not None


def test_llamacpp_remove_raises_when_available() -> None:
    from modeldock.common.errors import DownloadError

    runtime = _fake_llamacpp_runtime(model_id="model.gguf")
    with pytest.raises(DownloadError):
        runtime.remove(ModelRef.parse("model.gguf"))


def test_llamacpp_status_reflects_health_probe() -> None:
    runtime = _fake_llamacpp_runtime(model_id="model.gguf")
    status = runtime.status()
    assert status.available is True


# =============================================================================
# Planned/offline adapter contract — Jan, GPT4All, vLLM.
# =============================================================================


@pytest.fixture(params=[JanRuntime, Gpt4AllRuntime, VllmRuntime], ids=lambda cls: cls.__name__)
def planned_runtime(request: pytest.FixtureRequest) -> RuntimePort:
    return request.param()  # type: ignore[no-any-return]


def test_planned_runtime_reports_unavailable(planned_runtime: RuntimePort) -> None:
    assert planned_runtime.is_available() is False


def test_planned_runtime_list_installed_raises(planned_runtime: RuntimePort) -> None:
    with pytest.raises(RuntimeUnavailableError):
        planned_runtime.list_installed()


def test_planned_runtime_pull_raises(planned_runtime: RuntimePort) -> None:
    with pytest.raises(RuntimeUnavailableError):
        planned_runtime.pull(ModelRef.parse("anything"))


def test_planned_runtime_remove_raises(planned_runtime: RuntimePort) -> None:
    with pytest.raises(RuntimeUnavailableError):
        planned_runtime.remove(ModelRef.parse("anything"))


def test_planned_runtime_status_is_consistent(planned_runtime: RuntimePort) -> None:
    status = planned_runtime.status()
    assert status.available is False
    assert status.device.value == "unknown"


# =============================================================================
# Registry backend coverage — every registered backend has contract tests.
# =============================================================================


def test_registry_backend_coverage() -> None:
    """Fail if a backend is registered without a corresponding adapter here.

    Guards against the situation the original issue calls out: a new adapter
    lands in ``RuntimeRegistry`` but nobody adds it to the port-contract
    suite, so it silently ships without contract coverage.
    """
    registry = RuntimeRegistry()
    registered_backends = set(registry.available_backends())
    tested_backends = {impl.backend for impl in _all_runtime_implementations()}
    missing = registered_backends - tested_backends
    assert not missing, (
        f"Backend(s) {sorted(b.value for b in missing)} are registered in "
        "RuntimeRegistry but have no port-contract coverage in "
        "_all_runtime_implementations(). Add the adapter to that list."
    )


# =============================================================================
# CachePort contract
# =============================================================================


@pytest.fixture
def cache_factory(tmp_path: Path) -> Callable[[], List[CachePort]]:
    def _make() -> List[CachePort]:
        from modeldock.adapters.cache import FilesystemCache

        return [FakeCache(), FilesystemCache(tmp_path / "fs_cache")]

    return _make


def test_cache_conforms_to_protocol(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        assert isinstance(impl, CachePort)


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


def test_cache_path_returns_str(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        path = impl.path()
        assert isinstance(path, str)
        assert path


def test_cache_evict_is_idempotent(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        ref = ModelRef.parse("llama3")
        impl.evict(ref)  # no-op on a missing entry, must not raise
        impl.record(ref, "latest", "sha", 10)
        impl.evict(ref)
        assert not impl.is_fresh(ref)


def test_cache_model_config_roundtrip(cache_factory: Callable[[], List[CachePort]]) -> None:
    for impl in cache_factory():
        ref = ModelRef.parse("llama3")
        assert impl.get_model_config(ref) is None
        impl.set_model_config(ref, {"temperature": 0.7})
        assert impl.get_model_config(ref) == {"temperature": 0.7}


# =============================================================================
# DownloaderPort contract
# =============================================================================


def _downloader_implementations() -> List[DownloaderPort]:
    from modeldock.adapters.downloaders import HttpDownloader, OllamaPullDownloader

    return [HttpDownloader(), OllamaPullDownloader()]


@pytest.fixture(params=_downloader_implementations(), ids=lambda impl: type(impl).__name__)
def downloader_impl(request: pytest.FixtureRequest) -> DownloaderPort:
    return request.param


def test_downloader_conforms_to_protocol(downloader_impl: DownloaderPort) -> None:
    assert isinstance(downloader_impl, DownloaderPort)


def test_downloader_pull_signature(downloader_impl: DownloaderPort) -> None:
    """pull() must fail via the domain error hierarchy, not silently.

    HttpDownloader.pull() is intentionally unsupported (that adapter requires
    download(spec, dest), not pull(ref)) and always raises DownloadError.
    OllamaPullDownloader.pull() delegates to the real Ollama runtime, which
    is not running in this test environment, so it too raises DownloadError
    (wrapping the underlying RuntimeUnavailableError) rather than returning a
    fabricated success or letting an unrelated exception escape. Asserting
    the concrete type and a non-empty message gives this test actual
    signal — it fails if a future change makes pull() return silently, or
    raise something outside the ModelDockError hierarchy.
    """
    from modeldock.common.errors import DownloadError

    ref = ModelRef.parse("llama3")
    with pytest.raises(DownloadError) as exc_info:
        downloader_impl.pull(ref)
    assert str(exc_info.value)
