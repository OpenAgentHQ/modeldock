"""CachePort — the contract for tracking installed/downloaded artifacts.

Pure interface. Implementation: FilesystemCache (manifest + content hashing).
See Architecture.md §8.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

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

    def clean(self) -> List[str]:
        """Remove orphaned/partial artifacts; return removed paths."""
        ...

    def status(self) -> List[Dict[str, Any]]:
        """Return a snapshot of all cached entries."""
        ...
