"""Unit tests for DownloadService, LifecycleOrchestrator, and ModelManager."""

from __future__ import annotations

import pytest

from modeldock.common.errors import DownloadError, ModelNotInstalledError
from modeldock.core.download import DownloadService
from modeldock.core.lifecycle import LifecycleOrchestrator
from modeldock.domain.model import ModelRef


def test_download_pull_records_on_success(
    fake_runtime: object, fake_cache: object, fake_progress: object
) -> None:
    svc = DownloadService(fake_runtime, fake_cache, fake_progress)
    ref = ModelRef.parse("llama3")
    result = svc.pull(ref)
    assert result.success
    assert fake_cache.is_fresh(ref)


def test_download_pull_raises_on_failure(
    fake_runtime: object, fake_cache: object
) -> None:
    fake_runtime.pull_should_fail = True
    svc = DownloadService(fake_runtime, fake_cache)
    with pytest.raises(DownloadError):
        svc.pull(ModelRef.parse("llama3"))


def test_download_verify(fake_runtime: object, fake_cache: object) -> None:
    svc = DownloadService(fake_runtime, fake_cache)
    ref = ModelRef.parse("llama3")
    assert not svc.verify(ref)
    fake_runtime.pull(ref)
    assert svc.verify(ref)


def test_lifecycle_load_when_installed(
    fake_runtime: object, fake_registry: object, fake_cache: object
) -> None:
    fake_runtime._installed = [ModelRef.parse("llama3")]
    orch = LifecycleOrchestrator(fake_runtime, fake_registry, fake_cache)
    client = orch.load("llama3")
    assert client == {"client": "llama3:latest"}


def test_lifecycle_load_auto_install_false_raises(
    fake_runtime: object, fake_registry: object, fake_cache: object
) -> None:
    orch = LifecycleOrchestrator(fake_runtime, fake_registry, fake_cache, auto_install=False)
    with pytest.raises(ModelNotInstalledError):
        orch.load("llama3")


def test_lifecycle_load_auto_install_true_pulls(
    fake_runtime: object, fake_registry: object, fake_cache: object, fake_events: object
) -> None:
    orch = LifecycleOrchestrator(
        fake_runtime, fake_registry, fake_cache, events=fake_events, auto_install=True
    )
    client = orch.load("llama3")
    assert client == {"client": "llama3:latest"}
    assert fake_runtime.is_installed(ModelRef.parse("llama3"))
    assert fake_events.before_pull_calls  # event fired
    assert fake_events.after_install_calls


def test_lifecycle_load_emits_events_on_install(
    fake_runtime: object, fake_registry: object, fake_cache: object, fake_events: object
) -> None:
    orch = LifecycleOrchestrator(
        fake_runtime, fake_registry, fake_cache, events=fake_events, auto_install=True
    )
    orch.load("llama3")
    assert fake_events.before_pull_calls
    assert fake_events.after_install_calls


def test_manager_list_and_search(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    assert mgr.list()
    assert mgr.search("llama")


def test_manager_install(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    ref = mgr.install("llama3")
    assert ref.name == "llama3"
    assert mgr.verify("llama3")


def test_manager_install_unknown_raises(manager_with_fakes: object) -> None:
    from modeldock.common.errors import ModelNotFoundError

    with pytest.raises(ModelNotFoundError):
        manager_with_fakes.install("ghost")


def test_manager_install_category(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    refs = mgr.install_category("chat")
    assert refs
    assert all(mgr.verify(r.name) for r in refs)


def test_manager_update(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    mgr.install("llama3")
    ref = mgr.update("llama3")
    assert ref.name == "llama3"


def test_manager_remove(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    mgr.install("llama3")
    assert mgr.verify("llama3")
    mgr.remove("llama3")
    assert not mgr.verify("llama3")


def test_manager_load_auto_install(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    client = mgr.load("llama3", auto_install=True)
    assert client == {"client": "llama3:latest"}


def test_manager_cache_service(manager_with_fakes: object) -> None:
    mgr = manager_with_fakes
    mgr.install("llama3")
    assert mgr.cache.status()
