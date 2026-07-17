"""DownloadService — orchestrates pulling a model via a runtime.

Composes a RuntimePort + ProgressPort. Verifies the result and records it in
the cache. See Architecture.md §10.
"""

from __future__ import annotations

from typing import Optional

from modeldock.common.errors import DownloadError
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef, ModelSpec
from modeldock.ports.cache import CachePort
from modeldock.ports.progress import ProgressPort
from modeldock.ports.runtime import PullResult, RuntimePort


class DownloadService:
    """Application service that pulls/installs a model."""

    def __init__(
        self,
        runtime: RuntimePort,
        cache: CachePort,
        progress: Optional[ProgressPort] = None,
    ) -> None:
        self._runtime = runtime
        self._cache = cache
        self._progress = progress
        self._logger = get_logger("core.download")

    def pull(self, ref: ModelRef, spec: Optional[ModelSpec] = None) -> PullResult:
        """Pull ``ref`` and record success in the cache."""
        self._logger.info("Pulling %s", ref.qualified_name())
        result = self._runtime.pull(ref, self._progress)
        if not result.success:
            raise DownloadError(ref.name, reason=result.error or "unknown")
        self._cache.record(
            ref=ref,
            tag=ref.tag,
            sha256=result.sha256 or "",
            size_bytes=result.bytes_downloaded,
        )
        return result

    def verify(self, ref: ModelRef) -> bool:
        """Verify ``ref`` is installed in the runtime."""
        return self._runtime.is_installed(ref)


__all__ = ["DownloadService"]
