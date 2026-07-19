"""Port-contract test suite.

Validates that ANY RuntimePort / CachePort implementation obeys the contract
defined by the ports. Adapters must pass these same tests (Architecture.md S13).
Parameterized over the fake and real implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List

import pytest

from modeldock.domain.model import Category, ModelRef, ModelSpec
from modeldock.ports.cache import CachePort
from modeldock.ports.runtime import PullResult, RuntimePort, RuntimeStatus

# --- RuntimePort contract ---------------------------------------------------


def _runtime_implementations() -> List[RuntimePort]:
    from tests.conftest import FakeRuntime

    return [FakeRuntime()]


@pytest.fixture(params=_runtime_implementations())
def runtime_impl(request: pytest.FixtureRequest) -> RuntimePort:
    return request.param


def test_runtime_backend_is_set(runtime_impl: RuntimePort) -> None:
    assert runtime_impl.backend is not None


def test_runtime_pull_then_installed(runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    result = runtime_impl.pull(ref)
    assert isinstance(result, PullResult)
    assert result.success
    assert runtime_impl.is_installed(ref)


def test_runtime_list_installed(runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    runtime_impl.pull(ref)
    assert ref in runtime_impl.list_installed()


def test_runtime_remove(runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    runtime_impl.pull(ref)
    runtime_impl.remove(ref)
    assert not runtime_impl.is_installed(ref)


def test_runtime_get_client(runtime_impl: RuntimePort) -> None:
    ref = ModelRef.parse("llama3")
    runtime_impl.pull(ref)
    client = runtime_impl.get_model_client(ref)
    assert client is not None


def test_runtime_default_tag(runtime_impl: RuntimePort) -> None:
    spec = ModelSpec(name="x", category=Category.CHAT)
    assert runtime_impl.default_tag_for(spec) == spec.default_tag


def test_runtime_status_contract(runtime_impl: RuntimePort) -> None:
    status = runtime_impl.status()
    assert isinstance(status, RuntimeStatus)
    assert status.backend is not None
    assert status.device.value in {"gpu", "cpu", "unknown"}


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
