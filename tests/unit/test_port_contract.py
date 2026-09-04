"""Port-contract test suite.

Validates that ANY RuntimePort / CachePort implementation obeys the contract
defined by the ports. Adapters must pass these same tests (Architecture.md S13).
Parameterized over the fake and real implementations.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, List

import pytest

from modeldock.domain.model import Category, ModelRef, ModelSpec
from modeldock.ports.cache import CachePort, ContentStorePort
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


# --- ContentStorePort contract ----------------------------------------------


def _content_store_implementations(root: Path) -> List[ContentStorePort]:
    from modeldock.adapters.cache import FilesystemCache

    return [FilesystemCache(root / "fs_store")]


def test_content_store_stores_identical_content_once(tmp_path: Path) -> None:
    """Any ContentStorePort must key weights by content, never by name."""
    for impl in _content_store_implementations(tmp_path):
        payload = b"identical weights"
        first = tmp_path / "first.bin"
        second = tmp_path / "second.bin"
        first.write_bytes(payload)
        second.write_bytes(payload)

        blob_a, digest_a = impl.store_blob(first)
        blob_b, digest_b = impl.store_blob(second)

        assert digest_a == digest_b == hashlib.sha256(payload).hexdigest()
        assert blob_a == blob_b
        assert impl.blob_path(digest_a) == blob_a
        assert impl.has_blob(digest_a)


def test_content_store_links_without_duplicating(tmp_path: Path) -> None:
    for impl in _content_store_implementations(tmp_path):
        src = tmp_path / "weights.bin"
        src.write_bytes(b"linkable weights")
        blob, digest = impl.store_blob(src)
        dest = tmp_path / "readable" / "model.gguf"

        assert impl.link_into(blob, dest) == dest
        assert dest.read_bytes() == blob.read_bytes()
        assert impl.has_blob(digest), "linking must not move or consume the blob"
