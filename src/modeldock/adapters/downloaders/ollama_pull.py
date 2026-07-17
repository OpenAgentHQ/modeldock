"""OllamaPullDownloader — delegates pulls to Ollama's native mechanism.

Ollama manages its own blob store; ModelDock only tracks progress and verifies
via the runtime. See Architecture.md §10.
"""

from __future__ import annotations

from typing import Any

from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.common.errors import DownloadError
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult


class OllamaPullDownloader:
    """Downloader that delegates to the Ollama runtime's native pull."""

    def __init__(self, registry: RuntimeRegistry | None = None) -> None:
        self._registry = registry or RuntimeRegistry()
        self._logger = get_logger("downloader.ollama")

    def download(self, spec: Any, dest: Any, progress: Any = None) -> Any:
        raise DownloadError(
            getattr(spec, "name", "?"),
            reason="OllamaPullDownloader uses pull(), not download().",
        )

    def pull(self, ref: ModelRef, progress: Any = None) -> PullResult:
        runtime = self._registry.get(RuntimeBackend.OLLAMA)
        try:
            return runtime.pull(ref, progress)
        except Exception as exc:
            raise DownloadError(ref.name, reason=str(exc)) from exc


__all__ = ["OllamaPullDownloader"]
