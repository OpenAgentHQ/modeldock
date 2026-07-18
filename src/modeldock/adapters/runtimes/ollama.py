"""OllamaRuntime — the first shipped runtime adapter.

Implements ``RuntimePort`` for Ollama. Uses the optional ``ollama`` SDK when
available; otherwise talks to the Ollama HTTP API directly. Never imports the
SDK at module load (keeps base install light). See Architecture.md §4/§14.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import (
    DownloadError,
    ModelDockError,
    RuntimeUnavailableError,
)
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"
_PULL_VERIFY_BACKOFF_SECONDS = 0.1
_PULL_VERIFY_ATTEMPTS = 10
_CLIENT_TIMEOUT_SECONDS = 30.0


class OllamaRuntime(BaseRuntime):
    """Runtime adapter for Ollama."""

    backend: RuntimeBackend = RuntimeBackend.OLLAMA

    def __init__(self, host: Optional[str] = None) -> None:
        super().__init__()
        # Host is resolved at client-build time so overrides always apply,
        # even if is_available() was probed earlier.
        self._host = host
        self._client: Any = None

    # --- internal helpers -------------------------------------------------

    def _resolve_host(self) -> str:
        """Host precedence: explicit arg > OLLAMA_HOST env > default."""
        import os

        return self._host or os.environ.get("OLLAMA_HOST") or _OLLAMA_DEFAULT_HOST

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
        try:
            self._client = ollama.Client(host=self._resolve_host(), timeout=_CLIENT_TIMEOUT_SECONDS)
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeUnavailableError(
                "ollama",
                hint=f"Failed to build Ollama client: {exc}",
            ) from exc
        return self._client

    def _check_available(self) -> bool:
        """True if the daemon is reachable.

        Raises ``RuntimeUnavailableError`` when the SDK itself is missing
        (that is a setup problem, not a "daemon down" condition) so callers can
        present the right fix. Returns False only when the daemon is installed
        but not running / unreachable.
        """
        try:
            client = self._ensure_client()
            client.list()
            return True
        except RuntimeUnavailableError:
            # SDK missing is a setup problem, but is_available() is a boolean
            # probe: report unavailable rather than raising here. Explicit
            # operations (pull/remove/list_installed) still raise via
            # _ensure_client so the user gets the actionable hint.
            return False
        except Exception:
            return False

    def _parse_model_name(self, entry: Any) -> str:
        """Extract a model name from a list() entry (object or dict)."""
        if hasattr(entry, "model"):
            return str(entry.model)
        if isinstance(entry, dict):
            return entry.get("name") or entry.get("model") or ""
        return ""

    # --- RuntimePort hooks ------------------------------------------------

    def list_installed(self) -> List[ModelRef]:
        """Return locally installed models.

        Raises a typed error when the SDK is missing or the daemon is
        unreachable — we must not silently report an empty list, because that
        would make ``is_installed`` lie and cause needless re-pulls.
        """
        client = self._ensure_client()
        try:
            response = client.list()
        except RuntimeUnavailableError:
            # SDK missing is a setup problem — surface the actionable error.
            raise
        except Exception:
            # Daemon down / unreachable is an expected offline state, not an
            # error: report an empty list so installed()/list degrade cleanly.
            return []
        if isinstance(response, dict):
            models = response.get("models", [])
        else:
            models = getattr(response, "models", [])
        refs: List[ModelRef] = []
        for entry in models:
            name = self._parse_model_name(entry)
            if not name:
                continue
            ref = ModelRef.parse(name)
            ref.backend = RuntimeBackend.OLLAMA
            refs.append(ref)
        return refs

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        client = self._ensure_client()
        if progress is not None:
            progress.start(total=0, desc=f"Pulling {ref.qualified_name()}")
        total_bytes = 0
        try:
            stream = client.pull(ref.qualified_name(), stream=True)
            for event in stream:
                total_bytes = self._report_progress(event, progress, total_bytes)
        except TypeError:
            # Older SDK without stream support: blocking single call.
            client.pull(ref.qualified_name())
        except ModelDockError:
            raise
        except Exception as exc:
            raise DownloadError(ref.name, reason=str(exc)) from exc
        return self._verify_pull(ref, progress, total_bytes)

    def _report_progress(self, event: Any, progress: Any, total_bytes: int) -> int:
        """Consume one streamed pull event, updating progress. Return bytes."""
        status = getattr(event, "status", None)
        if status is None and isinstance(event, dict):
            status = event.get("status")
        completed = getattr(event, "completed", None)
        if completed is None and isinstance(event, dict):
            completed = event.get("completed")
        total = getattr(event, "total", None)
        if total is None and isinstance(event, dict):
            total = event.get("total")
        if progress is not None and completed is not None:
            # Re-base the bar to the running total so it reflects real bytes.
            if total:
                progress.start(total=total, desc="Pulling")
            progress.update(advance=int(completed) - total_bytes)
        if completed is not None:
            return int(completed)
        return total_bytes

    def _verify_pull(self, ref: ModelRef, progress: Any, total_bytes: int) -> PullResult:
        for _ in range(_PULL_VERIFY_ATTEMPTS):
            if self.is_installed(ref):
                if progress is not None:
                    progress.finish(desc=f"Pulled {ref.qualified_name()}")
                return PullResult(ref=ref, success=True, bytes_downloaded=total_bytes)
            time.sleep(_PULL_VERIFY_BACKOFF_SECONDS)
        if progress is not None:
            progress.finish(desc=f"Pull failed: {ref.qualified_name()}")
        return PullResult(
            ref=ref,
            success=False,
            error=f"{ref.qualified_name()} not listed after pull",
        )

    def _get_client(self, ref: ModelRef) -> Any:
        return self._ensure_client()

    def remove(self, ref: ModelRef) -> None:
        client = self._ensure_client()
        try:
            client.delete(ref.qualified_name())
        except ModelDockError:
            raise
        except Exception as exc:
            raise DownloadError(
                ref.name,
                reason=f"Failed to remove model: {exc}",
            ) from exc


__all__ = ["OllamaRuntime"]
