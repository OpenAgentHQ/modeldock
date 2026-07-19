"""Shared pytest fixtures for ModelDock tests.

Provides fake implementations of every port so core logic is testable without
Ollama installed. See Architecture.md S13 (fixtures) and AGENT.md (testing).
"""

from __future__ import annotations

from typing import Any, List, Optional

import pytest

from modeldock.domain.model import (
    Capability,
    Category,
    Device,
    ModelRef,
    ModelSpec,
    RuntimeBackend,
)
from modeldock.ports.cache import CachePort
from modeldock.ports.events import EventPort
from modeldock.ports.progress import ProgressPort
from modeldock.ports.registry import RegistryPort
from modeldock.ports.runtime import PullResult, RuntimePort, RuntimeStatus


class FakeProgress(ProgressPort):
    """Records progress calls for assertions."""

    def __init__(self) -> None:
        self.calls: List[str] = []
        self.total = 0

    def start(self, total: int, desc: str = "") -> None:
        self.total = total
        self.calls.append(f"start:{desc}")

    def update(self, advance: int) -> None:
        self.calls.append(f"update:{advance}")

    def finish(self, desc: str = "") -> None:
        self.calls.append(f"finish:{desc}")


class FakeEvents(EventPort):
    """Records lifecycle events for assertions."""

    def __init__(self) -> None:
        self.before_pull_calls: List[ModelRef] = []
        self.after_install_calls: List[Any] = []
        self.on_error_calls: List[Any] = []

    def before_pull(self, ref: ModelRef) -> None:
        self.before_pull_calls.append(ref)

    def after_install(self, ref: ModelRef, result: Any) -> None:
        self.after_install_calls.append((ref, result))

    def on_error(self, ref: ModelRef, error: Exception) -> None:
        self.on_error_calls.append((ref, error))


class FakeCache(CachePort):
    """In-memory cache implementation for tests."""

    def __init__(self) -> None:
        self.entries: dict = {}
        self.cleaned: List[str] = []

    def is_fresh(self, ref: ModelRef) -> bool:
        return self._key(ref) in self.entries

    def record(self, ref: ModelRef, tag: str, sha256: str, size_bytes: int) -> None:
        self.entries[self._key(ref)] = {
            "name": ref.name,
            "tag": tag,
            "sha256": sha256,
            "size_bytes": size_bytes,
        }

    def get_record(self, ref: ModelRef) -> Optional[dict]:
        return self.entries.get(self._key(ref))

    def clean(self, force: bool = False) -> List[str]:
        removed = [k for k, v in self.entries.items() if force or not v.get("sha256")]
        for k in removed:
            del self.entries[k]
        self.cleaned.extend(removed)
        return removed

    def status(self) -> List[dict]:
        return list(self.entries.values())

    @staticmethod
    def _key(ref: ModelRef) -> str:
        return f"{ref.name}:{ref.tag}"


class FakeRuntime(RuntimePort):
    """Configurable fake runtime for core/lifecycle tests."""

    backend = RuntimeBackend.OLLAMA

    def __init__(
        self,
        available: bool = True,
        installed: Optional[List[ModelRef]] = None,
        pull_should_fail: bool = False,
    ) -> None:
        self._available = available
        self._installed = installed or []
        self.pull_should_fail = pull_should_fail
        self.pulled: List[ModelRef] = []
        self.removed: List[ModelRef] = []
        self.clients: List[ModelRef] = []

    def is_available(self) -> bool:
        return self._available

    def list_installed(self) -> List[ModelRef]:
        return list(self._installed)

    def is_installed(self, ref: ModelRef) -> bool:
        return any(r.name == ref.name and r.tag == ref.tag for r in self._installed)

    def pull(self, ref: ModelRef, progress: Any = None) -> PullResult:
        if self.pull_should_fail:
            return PullResult(ref=ref, success=False, error="boom")
        self._installed.append(ref)
        self.pulled.append(ref)
        return PullResult(ref=ref, success=True, bytes_downloaded=10)

    def remove(self, ref: ModelRef) -> None:
        self._installed = [
            r for r in self._installed if not (r.name == ref.name and r.tag == ref.tag)
        ]
        self.removed.append(ref)

    def get_model_client(self, ref: ModelRef) -> Any:
        self.clients.append(ref)
        return {"client": ref.qualified_name()}

    def default_tag_for(self, spec: ModelSpec) -> str:
        return spec.default_tag

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(
            backend=self.backend,
            available=self._available,
            device=Device.UNKNOWN,
        )

    def run(self, ref: ModelRef, prompt: Optional[str] = None, **opts: Any) -> Any:
        from modeldock.ports.runtime import RunResult

        return RunResult(ref=ref, success=True, completion_tokens=1)


class FakeRegistry(RegistryPort):
    """In-memory registry seeded with a few specs."""

    def __init__(self, specs: Optional[List[ModelSpec]] = None) -> None:
        self.specs = specs or [self._sample_spec()]
        self.by_name: dict = {s.name: s for s in self.specs}

    @staticmethod
    def _sample_spec() -> ModelSpec:
        return ModelSpec(
            name="llama3",
            aliases=["llama3", "llama-3"],
            category=Category.CHAT,
            capabilities=[Capability.CHAT, Capability.COMPLETION],
            default_tag="latest",
            variants=[{"tag": "8b", "params": "8B"}],
            description="Sample model.",
            backend_hints=[RuntimeBackend.OLLAMA],
        )

    def search(self, query: str) -> List[ModelSpec]:
        q = query.strip().lower()
        return [s for s in self.specs if q in s.name.lower() or q in s.description.lower()]

    def get(self, ref: ModelRef) -> ModelSpec:
        spec = self.by_name.get(ref.name)
        if spec is None:
            from modeldock.common.errors import ModelNotFoundError

            raise ModelNotFoundError(ref.name)
        return spec

    def by_category(self, category: Category) -> List[ModelSpec]:
        return [s for s in self.specs if s.category == category]

    def recommend(self, task: str) -> List[ModelSpec]:
        return [s for s in self.specs if task.lower() in s.name.lower()]

    def list_all(self) -> List[ModelSpec]:
        return list(self.specs)


@pytest.fixture
def fake_progress() -> FakeProgress:
    return FakeProgress()


@pytest.fixture
def fake_events() -> FakeEvents:
    return FakeEvents()


@pytest.fixture
def fake_cache() -> FakeCache:
    return FakeCache()


@pytest.fixture
def fake_runtime() -> FakeRuntime:
    return FakeRuntime()


@pytest.fixture
def fake_registry() -> FakeRegistry:
    return FakeRegistry()


@pytest.fixture
def manager_with_fakes(
    fake_runtime: FakeRuntime,
    fake_registry: FakeRegistry,
    fake_cache: FakeCache,
    fake_progress: FakeProgress,
    fake_events: FakeEvents,
) -> Any:
    """A ModelManager wired entirely with fakes (no Ollama needed)."""
    from modeldock.core.manager import ModelManager

    return ModelManager(
        runtime=fake_runtime,
        registry=fake_registry,
        cache=fake_cache,
        events=fake_events,
    )
