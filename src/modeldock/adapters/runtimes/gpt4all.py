"""GPT4All runtime adapter (planned). Implements RuntimePort; not yet shipped."""

from __future__ import annotations

from typing import Any, List

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult


class Gpt4AllRuntime(BaseRuntime):
    """Planned runtime adapter for GPT4All."""

    backend: RuntimeBackend = RuntimeBackend.GPT4ALL

    def _check_available(self) -> bool:
        return False

    def list_installed(self) -> List[ModelRef]:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")

    def _get_client(self, ref: ModelRef) -> Any:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")

    def remove(self, ref: ModelRef) -> None:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")


__all__ = ["Gpt4AllRuntime"]
