"""GPT4All local model-directory discovery.

The adapter deliberately stops at discovery for issue #30. It does not download
or load models until the remaining GPT4All runtime work is implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult


class Gpt4AllRuntime(BaseRuntime):
    """Discover models already present in a GPT4All models directory."""

    backend: RuntimeBackend = RuntimeBackend.GPT4ALL

    def __init__(self, models_dir: Path | None = None) -> None:
        super().__init__()
        self._models_dir = models_dir or Path.home() / ".cache" / "gpt4all"

    def _check_available(self) -> bool:
        return self._models_dir.is_dir()

    def list_installed(self) -> List[ModelRef]:
        if not self._models_dir.is_dir():
            return []
        refs: List[ModelRef] = []
        for path in sorted(self._models_dir.iterdir(), key=lambda path: path.name):
            if path.is_file() and path.suffix.lower() in {".gguf", ".bin"}:
                refs.append(ModelRef.parse(path.stem))
        return refs

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")

    def _get_client(self, ref: ModelRef) -> Any:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")

    def remove(self, ref: ModelRef) -> None:
        raise RuntimeUnavailableError("gpt4all", hint="Adapter planned, not shipped.")


__all__ = ["Gpt4AllRuntime"]
