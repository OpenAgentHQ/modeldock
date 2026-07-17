"""Jan AI runtime adapter (planned). Implements RuntimePort; not yet shipped."""

from __future__ import annotations

from typing import Any, List

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult


class JanRuntime(BaseRuntime):
    """Planned runtime adapter for Jan AI."""

    backend: RuntimeBackend = RuntimeBackend.JAN

    def _check_available(self) -> bool:
        return False

    def list_installed(self) -> List[ModelRef]:
        raise RuntimeUnavailableError("jan", hint="Adapter planned, not shipped.")

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        raise RuntimeUnavailableError("jan", hint="Adapter planned, not shipped.")

    def _get_client(self, ref: ModelRef) -> Any:
        raise RuntimeUnavailableError("jan", hint="Adapter planned, not shipped.")

    def remove(self, ref: ModelRef) -> None:
        raise RuntimeUnavailableError("jan", hint="Adapter planned, not shipped.")


__all__ = ["JanRuntime"]
