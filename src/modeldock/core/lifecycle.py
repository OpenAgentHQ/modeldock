"""LifecycleOrchestrator - the missing to download to verify to load flow."""

from __future__ import annotations

from typing import Any, Optional

from modeldock.common.errors import ModelNotInstalledError
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef, ModelSpec
from modeldock.ports.cache import CachePort
from modeldock.ports.events import EventPort
from modeldock.ports.progress import ProgressPort
from modeldock.ports.registry import RegistryPort
from modeldock.ports.runtime import RuntimePort


class LifecycleOrchestrator:
    """Orchestrates the full model lifecycle for one runtime."""

    def __init__(
        self,
        runtime: RuntimePort,
        registry: RegistryPort,
        cache: CachePort,
        progress: Optional[ProgressPort] = None,
        events: Optional[EventPort] = None,
        auto_install: bool = False,
    ) -> None:
        self._runtime = runtime
        self._registry = registry
        self._cache = cache
        self._progress = progress
        self._events = events
        self._auto_install = auto_install
        self._logger = get_logger("core.lifecycle")

    def load(self, name: str, auto_install: Optional[bool] = None) -> Any:
        """Resolve, ensure installed, verify, and return a ready client."""
        ref = ModelRef.parse(name, backend=self._runtime.backend)
        self._resolve(ref)
        do_install = self._auto_install if auto_install is None else auto_install
        ev = self._events

        if not self._runtime.is_installed(ref):
            if not do_install:
                raise ModelNotInstalledError(ref.qualified_name(), auto_install=False)
            if ev is not None:
                ev.before_pull(ref)
            self._runtime.pull(ref, self._progress)
            self._cache.record(ref, ref.tag, "", 0)
            if ev is not None:
                ev.after_install(ref, None)

        if not self._runtime.is_installed(ref):
            raise ModelNotInstalledError(ref.qualified_name(), auto_install=do_install)

        return self._runtime.get_model_client(ref)

    def _resolve(self, ref: ModelRef) -> ModelSpec:
        return self._registry.get(ref)


__all__ = ["LifecycleOrchestrator"]
