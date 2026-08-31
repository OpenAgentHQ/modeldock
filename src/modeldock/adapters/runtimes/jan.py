"""Jan AI runtime adapter (planned). Implements RuntimePort; not yet shipped."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, List

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import Capability, ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult

_JAN_CAPABILITY_MAP: dict[str, Capability] = {
    "completion": Capability.COMPLETION,
    "chat": Capability.CHAT,
    "embeddings": Capability.EMBED,
    "vision": Capability.VISION,
    "reasoning": Capability.REASONING,
    "tools": Capability.TOOL_USE,
}


def _map_jan_capabilities(raw_capabilities: object) -> List[Capability]:
    """Map Jan capability strings without trusting runtime metadata shape."""
    if not isinstance(raw_capabilities, Sequence) or isinstance(
        raw_capabilities, (str, bytes, bytearray)
    ):
        return []

    mapped: List[Capability] = []
    seen: set[Capability] = set()
    for raw_capability in raw_capabilities:
        if not isinstance(raw_capability, str):
            continue
        capability = _JAN_CAPABILITY_MAP.get(raw_capability.strip().lower())
        if capability is not None and capability not in seen:
            mapped.append(capability)
            seen.add(capability)
    return mapped


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
