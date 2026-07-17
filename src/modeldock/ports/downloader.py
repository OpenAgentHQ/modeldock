"""DownloaderPort — the contract for moving model bytes.

Pure interface. Implementations: HttpDownloader, OllamaPullDownloader.
See Architecture.md §10.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from modeldock.domain.model import ModelRef, ModelSpec


@runtime_checkable
class DownloaderPort(Protocol):
    """Abstraction over a byte-mover for models."""

    def download(self, spec: ModelSpec, dest: Path, progress: Any = None) -> Path:
        """Download ``spec`` to ``dest``, reporting via ``progress``."""
        ...

    def pull(self, ref: ModelRef, progress: Any = None) -> Any:
        """Pull ``ref`` via the runtime-native mechanism; return a result."""
        ...
