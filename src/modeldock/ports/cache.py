"""CachePort — the contract for tracking installed/downloaded artifacts.

Pure interface. Implementation: FilesystemCache (manifest + content hashing).
See Architecture.md §8.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from modeldock.domain.model import ModelRef


@runtime_checkable
class CachePort(Protocol):
    """Abstraction over the local model cache."""

    def is_fresh(self, ref: ModelRef) -> bool:
        """Return True if ``ref`` is cached/installed and up to date."""
        ...

    def record(self, ref: ModelRef, tag: str, sha256: str, size_bytes: int) -> None:
        """Record an installed/downloaded artifact in the manifest."""
        ...

    def get_record(self, ref: ModelRef) -> Optional[Dict[str, Any]]:
        """Return the cached manifest entry for ``ref``, if any."""
        ...

    def clean(self, force: bool = False) -> List[str]:
        """Remove orphaned/partial artifacts; return removed paths.

        Safe by default: only corrupt/partial manifest entries are removed.
        Pass ``force=True`` to wipe every cached entry.
        """
        ...

    def status(self) -> List[Dict[str, Any]]:
        """Return a snapshot of all cached entries."""
        ...

    def evict(self, ref: ModelRef) -> None:
        """Remove the manifest entry for ``ref`` if present (no-op otherwise)."""
        ...

    def path(self) -> str:
        """Return the cache directory path."""
        ...

    def get_model_config(self, ref: ModelRef) -> Optional[Dict[str, Any]]:
        """Return the user config stored for ``ref``, or None if not set."""
        ...

    def set_model_config(self, ref: ModelRef, config: Dict[str, Any]) -> None:
        """Store ``config`` as the user config for ``ref``."""
        ...


@runtime_checkable
class ContentStorePort(Protocol):
    """Content-addressed storage for downloaded weights.

    Optional companion to :class:`CachePort`, implemented by caches that own
    the artifact bytes (``FilesystemCache``). Keying weights by SHA-256 is what
    stops two refs that resolve to byte-identical files from costing disk
    twice. Callers feature-detect it with ``isinstance`` and fall back to a
    plain :class:`CachePort` when the cache does not store blobs.
    """

    def has_blob(self, sha256: str) -> bool:
        """Return True if weights with this digest are already stored."""
        ...

    def blob_path(self, sha256: str) -> Path:
        """Return the content-addressed location for ``sha256``."""
        ...

    def store_blob(self, src: Path, sha256: Optional[str] = None) -> Tuple[Path, str]:
        """Move ``src`` into the store; return ``(blob_path, digest)``.

        Discards ``src`` and returns the existing blob when the same content is
        already stored. Raises ``CacheError`` if ``sha256`` is given and the
        content does not hash to it.
        """
        ...

    def link_into(self, blob: Path, dest: Path) -> Path:
        """Expose ``blob`` at ``dest`` without duplicating its bytes."""
        ...

    def record_artifact(
        self,
        ref: ModelRef,
        tag: str,
        sha256: str,
        size_bytes: int,
        path: Path,
    ) -> None:
        """Record a stored artifact together with its blob digest and path."""
        ...
