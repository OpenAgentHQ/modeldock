"""RuntimePort — the contract every model runtime adapter must honor.

Pure interface (typing.Protocol). No implementation, no I/O here.
See Architecture.md §4 for the design rationale.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Protocol, runtime_checkable

from modeldock.domain.model import ModelRef, ModelSpec, RuntimeBackend


@runtime_checkable
class RuntimePort(Protocol):
    """Abstraction over a local model runtime (Ollama, LM Studio, ...)."""

    @property
    def backend(self) -> RuntimeBackend:
        """Identify the runtime backend."""
        ...

    def is_available(self) -> bool:
        """Return True if the runtime is installed and reachable."""
        ...

    def list_installed(self) -> List[ModelRef]:
        """Return models present locally in this runtime."""
        ...

    def is_installed(self, ref: ModelRef) -> bool:
        """Return True if ``ref`` is present locally."""
        ...

    def pull(self, ref: ModelRef, progress: Any = None) -> PullResult:
        """Download/install ``ref``, reporting via ``progress`` (ProgressPort)."""
        ...

    def remove(self, ref: ModelRef) -> None:
        """Uninstall ``ref`` from the runtime."""
        ...

    def get_model_client(self, ref: ModelRef) -> Any:
        """Return a ready-to-use, runtime-native client for ``ref``."""
        ...

    def default_tag_for(self, spec: ModelSpec) -> str:
        """Resolve the default variant tag for a model spec."""
        ...


class PullResult:
    """Result of a pull/install operation (returned by ``RuntimePort.pull``)."""

    def __init__(
        self,
        ref: ModelRef,
        success: bool,
        path: Optional[Path] = None,
        sha256: Optional[str] = None,
        bytes_downloaded: int = 0,
        error: Optional[str] = None,
    ) -> None:
        self.ref = ref
        self.success = success
        self.path = path
        self.sha256 = sha256
        self.bytes_downloaded = bytes_downloaded
        self.error = error

    def __repr__(self) -> str:
        state = "ok" if self.success else f"failed({self.error})"
        return f"PullResult({self.ref.qualified_name()}, {state})"
