"""BaseRuntime — shared logic for concrete runtime adapters.

Provides alias resolution, availability caching, and error normalization so
each concrete runtime only implements runtime-specific calls. See Architecture.md §4.
"""

from __future__ import annotations

from typing import Any, List, Optional

from modeldock.common.errors import (
    ModelNotInstalledError,
    RuntimeUnavailableError,
)
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef, ModelSpec, RuntimeBackend
from modeldock.ports.runtime import PullResult

_AVAILABILITY_TTL = 5.0


class BaseRuntime:
    """Mixin/base providing shared RuntimePort behavior.

    Concrete runtimes subclass this and implement the ``_``-prefixed hooks.
    """

    backend: RuntimeBackend = RuntimeBackend.OLLAMA

    def __init__(self) -> None:
        self._logger = get_logger(f"runtime.{self.backend.value}")
        self._availability: Optional[bool] = None
        self._availability_checked_at: float = 0.0

    # --- shared, final behavior -------------------------------------------

    def is_available(self) -> bool:
        """Return cached availability, refreshing if stale."""
        import time

        now = time.monotonic()
        if self._availability is None or (now - self._availability_checked_at) > _AVAILABILITY_TTL:
            self._availability = self._check_available()
            self._availability_checked_at = now
        return self._availability

    def is_installed(self, ref: ModelRef) -> bool:
        """Presence check via ``list_installed``."""
        return any(
            existing.name == ref.name and existing.tag == ref.tag
            for existing in self.list_installed()
        )

    def default_tag_for(self, spec: ModelSpec) -> str:
        """Resolve the default tag for a spec (runtime may override)."""
        return spec.default_tag

    def pull(self, ref: ModelRef, progress: Any = None) -> PullResult:
        """Normalized pull: checks availability, delegates to ``_do_pull``."""
        if not self.is_available():
            raise RuntimeUnavailableError(
                self.backend.value,
                hint="Install the runtime or choose another backend.",
            )
        self._logger.info("Pulling %s", ref.qualified_name())
        try:
            return self._do_pull(ref, progress)
        except RuntimeUnavailableError:
            raise
        except Exception as exc:  # normalize unexpected failures
            self._logger.error("Pull failed: %s", exc)
            return PullResult(ref=ref, success=False, error=str(exc))

    def get_model_client(self, ref: ModelRef) -> Any:
        """Return a client, ensuring the model is installed."""
        if not self.is_installed(ref):
            raise ModelNotInstalledError(ref.qualified_name())
        return self._get_client(ref)

    # --- hooks for concrete runtimes --------------------------------------

    def _check_available(self) -> bool:
        """Return whether the runtime is installed/reachable."""
        raise NotImplementedError

    def list_installed(self) -> List[ModelRef]:
        """Return locally installed models."""
        raise NotImplementedError

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        """Perform the actual pull; return a ``PullResult``."""
        raise NotImplementedError

    def _get_client(self, ref: ModelRef) -> Any:
        """Return a runtime-native client for ``ref``."""
        raise NotImplementedError

    def remove(self, ref: ModelRef) -> None:
        """Uninstall ``ref``."""
        raise NotImplementedError


__all__ = ["BaseRuntime"]
