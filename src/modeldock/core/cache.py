"""CacheService — smart caching over a CachePort.

Wraps the filesystem cache with freshness checks and cleanup. See Architecture.md §8.
"""

from __future__ import annotations

from typing import Any, Dict, List

from modeldock.domain.model import ModelRef
from modeldock.ports.cache import CachePort


class CacheService:
    """Application service for cache management."""

    def __init__(self, cache: CachePort) -> None:
        self._cache = cache

    def is_fresh(self, ref: ModelRef) -> bool:
        """Return True if ``ref`` is cached/installed and up to date."""
        return self._cache.is_fresh(ref)

    def record(self, ref: ModelRef, tag: str, sha256: str, size_bytes: int) -> None:
        """Record an installed/downloaded artifact."""
        self._cache.record(ref, tag, sha256, size_bytes)

    def status(self) -> List[Dict[str, Any]]:
        """Return a snapshot of cached entries."""
        return self._cache.status()

    def clean(self) -> List[str]:
        """Remove orphaned/partial artifacts; return removed paths."""
        return self._cache.clean()

    def path(self) -> str:
        """Return the cache directory path (best-effort)."""
        record = self._cache.get_record(ModelRef.parse("__none__"))
        return str(record) if record else "<cache>"


__all__ = ["CacheService"]
