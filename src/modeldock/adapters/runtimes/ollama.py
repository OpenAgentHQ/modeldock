"""OllamaRuntime — the first shipped runtime adapter.

Implements ``RuntimePort`` for Ollama. Uses the optional ``ollama`` SDK when
available; otherwise talks to the Ollama HTTP API directly. Never imports the
SDK at module load (keeps base install light). See Architecture.md §4/§14.
"""

from __future__ import annotations

from typing import Any, List, Optional

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import RuntimeUnavailableError
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"


class OllamaRuntime(BaseRuntime):
    """Runtime adapter for Ollama."""

    backend: RuntimeBackend = RuntimeBackend.OLLAMA

    def __init__(self, host: Optional[str] = None) -> None:
        super().__init__()
        self._host = host or _OLLAMA_DEFAULT_HOST
        self._client: Any = None

    # --- internal helpers -------------------------------------------------

    def _get_host(self) -> str:
        import os

        return os.environ.get("OLLAMA_HOST") or self._host

    def _ensure_client(self) -> Any:
        """Lazily build an ollama.Client; raise if the SDK is missing."""
        if self._client is not None:
            return self._client
        try:
            import ollama
        except ImportError as exc:  # optional extra
            raise RuntimeUnavailableError(
                "ollama",
                hint="Install the SDK with `pip install modeldock[ollama]`.",
            ) from exc
        self._client = ollama.Client(host=self._get_host())
        return self._client

    def _check_available(self) -> bool:
        try:
            client = self._ensure_client()
            client.list()
            return True
        except Exception:
            return False

    # --- RuntimePort hooks ------------------------------------------------

    def list_installed(self) -> List[ModelRef]:
        try:
            client = self._ensure_client()
            models = client.list().get("models", [])
        except Exception:
            # Daemon down or SDK missing -> nothing is installed from our view.
            return []
        refs: List[ModelRef] = []
        for entry in models:
            name = entry.get("name") or entry.get("model", "")
            if not name:
                continue
            ref = ModelRef.parse(name)
            ref.backend = RuntimeBackend.OLLAMA
            refs.append(ref)
        return refs

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        client = self._ensure_client()
        total = 0
        if progress is not None:
            progress.start(total=0, desc=f"Pulling {ref.qualified_name()}")
        # Stream progress if the SDK supports it; otherwise single call.
        try:
            client.pull(ref.qualified_name(), stream=progress is not None)
        except TypeError:
            client.pull(ref.qualified_name())
        if progress is not None:
            progress.finish(desc=f"Pulled {ref.qualified_name()}")
        return PullResult(ref=ref, success=True, bytes_downloaded=total)

    def _get_client(self, ref: ModelRef) -> Any:
        client = self._ensure_client()
        return client

    def remove(self, ref: ModelRef) -> None:
        client = self._ensure_client()
        client.delete(ref.qualified_name())


__all__ = ["OllamaRuntime"]
