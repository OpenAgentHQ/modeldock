"""LMStudioRuntime — runtime adapter for LM Studio.

Implements ``RuntimePort`` for LM Studio's local server API. Uses the
OpenAI-compatible endpoints at http://localhost:1234 (default). See
Architecture.md §4/§14.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import (
    DownloadError,
    ModelDockError,
    ModelNotInstalledError,
    RuntimeUnavailableError,
)
from modeldock.domain.model import Device, ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult, RunResult

_DEFAULT_HOST = "http://localhost:1234"
_DEFAULT_TIMEOUT = 30.0
_LIST_VERIFY_BACKOFF_SECONDS = 0.1
_LIST_VERIFY_ATTEMPTS = 10


class LMStudioRuntime(BaseRuntime):
    """Runtime adapter for LM Studio."""

    backend: RuntimeBackend = RuntimeBackend.LM_STUDIO

    def __init__(
        self,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._host = host
        self._api_key = api_key
        self._client: Any = None

    # --- internal helpers -------------------------------------------------

    def _resolve_host(self) -> str:
        """Host precedence: explicit arg > LM_STUDIO_HOST env > default."""
        import os

        return self._host or os.environ.get("LM_STUDIO_HOST") or _DEFAULT_HOST

    def _resolve_api_key(self) -> Optional[str]:
        """API key precedence: explicit arg > LM_API_TOKEN env > None."""
        import os

        return self._api_key or os.environ.get("LM_API_TOKEN")

    def _ensure_client(self) -> Any:
        """Lazily build an OpenAI-compatible client for LM Studio."""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeUnavailableError(
                "lmstudio",
                hint="Install the OpenAI SDK with `pip install openai`.",
            ) from exc
        try:
            api_key = self._resolve_api_key() or "lm-studio"
            self._client = OpenAI(
                base_url=f"{self._resolve_host()}/v1",
                api_key=api_key,
                timeout=_DEFAULT_TIMEOUT,
            )
        except Exception as exc:
            raise RuntimeUnavailableError(
                "lmstudio",
                hint=f"Failed to build LM Studio client: {exc}",
            ) from exc
        return self._client

    def _ensure_http_client(self) -> Any:
        """Build an httpx client for native LM Studio API calls."""
        import httpx

        api_key = self._resolve_api_key()
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return httpx.Client(
            base_url=self._resolve_host(),
            headers=headers,
            timeout=_DEFAULT_TIMEOUT,
        )

    def _check_available(self) -> bool:
        """True if the LM Studio server is reachable."""
        try:
            http_client = self._ensure_http_client()
            response = http_client.get("/v1/models")
            return bool(response.status_code == 200)
        except Exception:
            return False

    def _parse_model_id(self, entry: Any) -> str:
        """Extract a model ID from a list() entry (object or dict)."""
        if hasattr(entry, "id"):
            return str(entry.id)
        if isinstance(entry, dict):
            return str(entry.get("id", ""))
        return ""

    # --- RuntimePort hooks ------------------------------------------------

    def list_installed(self) -> List[ModelRef]:
        """Return locally installed models.

        Queries LM Studio's /v1/models endpoint. Returns empty list if
        server is unreachable (expected offline state).
        """
        try:
            http_client = self._ensure_http_client()
            response = http_client.get("/v1/models")
            if response.status_code != 200:
                return []
            data = response.json()
            models = data.get("data", [])
        except Exception:
            return []

        refs: List[ModelRef] = []
        for entry in models:
            model_id = self._parse_model_id(entry)
            if not model_id:
                continue
            # LM Studio uses author/model-name format
            # Parse into ModelRef with name and tag
            if "/" in model_id:
                name, tag = model_id.rsplit("/", 1)
            elif ":" in model_id:
                name, tag = model_id.split(":", 1)
            else:
                name, tag = model_id, "latest"
            ref = ModelRef(name=name, tag=tag, backend=RuntimeBackend.LM_STUDIO)
            refs.append(ref)
        return refs

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        """Download/install a model via LM Studio's native API.

        LM Studio manages models through its UI or native API. This method
        attempts to download the model using the /api/v1/models/download
        endpoint if available, otherwise raises an error directing users to
        use LM Studio's UI.
        """
        # Try native download API first
        try:
            http_client = self._ensure_http_client()
            model_id = ref.qualified_name()
            if progress is not None:
                progress.start(total=0, desc=f"Downloading {model_id}")

            response = http_client.post(
                "/api/v1/models/download",
                json={"model": model_id},
            )

            if response.status_code == 200:
                # Poll for download completion
                return self._verify_download(ref, progress, http_client)
            else:
                # Download API not available or failed
                if progress is not None:
                    progress.finish(desc=f"Download not available for {model_id}")
                return PullResult(
                    ref=ref,
                    success=False,
                    error=(
                        f"LM Studio download API not available. "
                        f"Please download '{model_id}' through LM Studio's UI."
                    ),
                )
        except Exception as exc:
            if progress is not None:
                progress.finish(desc=f"Download failed: {ref.qualified_name()}")
            return PullResult(
                ref=ref,
                success=False,
                error=f"Download failed: {exc}",
            )

    def _verify_download(
        self,
        ref: ModelRef,
        progress: Any,
        http_client: Any,
    ) -> PullResult:
        """Poll download status until complete or timeout."""
        model_id = ref.qualified_name()
        for _ in range(_LIST_VERIFY_ATTEMPTS):
            try:
                response = http_client.get("/api/v1/models/download/status")
                if response.status_code == 200:
                    status = response.json()
                    if status.get("status") == "completed":
                        if progress is not None:
                            progress.finish(desc=f"Downloaded {model_id}")
                        return PullResult(ref=ref, success=True)
                    elif status.get("status") == "failed":
                        error_msg = status.get("error", "Unknown error")
                        if progress is not None:
                            progress.finish(desc=f"Download failed: {model_id}")
                        return PullResult(
                            ref=ref,
                            success=False,
                            error=f"Download failed: {error_msg}",
                        )
            except Exception:  # nosec B110 - best-effort polling
                pass
            time.sleep(_LIST_VERIFY_BACKOFF_SECONDS)

        if progress is not None:
            progress.finish(desc=f"Download timeout: {model_id}")
        return PullResult(
            ref=ref,
            success=False,
            error=f"Download timeout for {model_id}",
        )

    def _get_client(self, ref: ModelRef) -> Any:
        """Return an OpenAI-compatible client for the model."""
        return self._ensure_client()

    def remove(self, ref: ModelRef) -> None:
        """Remove a model from LM Studio.

        LM Studio manages model storage. This method attempts to unload
        the model and suggests using LM Studio's UI for full removal.
        """
        if ref.is_cloud:
            raise DownloadError(
                ref.name,
                reason=(
                    f"{ref.qualified_name()} is a cloud/subscription model and "
                    "cannot be removed locally."
                ),
            )

        model_id = ref.qualified_name()
        try:
            # Try to unload the model first
            http_client = self._ensure_http_client()
            response = http_client.post(
                "/api/v1/models/unload",
                json={"model": model_id},
            )
            if response.status_code == 200:
                self._logger.info("Unloaded model: %s", model_id)
                return
        except Exception:  # nosec B110 - best-effort unload
            pass

        # If unload fails, suggest using LM Studio UI
        raise DownloadError(
            ref.name,
            reason=(
                f"LM Studio manages model storage. "
                f"Please remove '{model_id}' through LM Studio's UI."
            ),
        )

    def run(
        self,
        ref: ModelRef,
        prompt: Optional[str] = None,
        **opts: Any,
    ) -> RunResult:
        """Run an interactive session, streaming tokens to stdout.

        When ``prompt`` is given, runs a single completion and returns. When
        ``prompt`` is ``None``, drops into a read-eval-print loop reading lines
        from stdin until EOF or a quit command. Requires the model to be
        installed locally.
        """
        if not self.is_installed(ref):
            raise ModelNotInstalledError(ref.qualified_name())
        client = self._ensure_client()
        if prompt is not None:
            return self._run_single(client, ref, prompt, **opts)
        return self._run_repl(client, ref, **opts)

    def _run_single(
        self,
        client: Any,
        ref: ModelRef,
        prompt: str,
        **opts: Any,
    ) -> RunResult:
        """Run one completion and stream tokens to stdout."""
        model_id = ref.qualified_name()
        try:
            # Use chat completions for better compatibility
            stream = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                **opts,
            )
            completion_tokens = 0
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    completion_tokens += 1
                    self._write(token)
            self._write("\n")
            return RunResult(
                ref=ref,
                success=True,
                prompt_tokens=0,
                completion_tokens=completion_tokens,
            )
        except ModelDockError:
            raise
        except Exception as exc:
            return RunResult(ref=ref, success=False, error=str(exc))

    def _run_repl(
        self,
        client: Any,
        ref: ModelRef,
        **opts: Any,
    ) -> RunResult:
        """Interactive read-eval-print loop until EOF or a quit command."""
        import sys

        completion_tokens = 0
        self._write(f">>> {ref.qualified_name()} (type 'exit' or Ctrl-D to quit)\n")
        while True:
            try:
                line = sys.stdin.readline()
            except EOFError:
                break
            if not line:
                break
            text = line.rstrip("\n")
            if text.strip().lower() in {"exit", "quit", "/exit", "/quit"}:
                break
            if not text.strip():
                continue
            result = self._run_single(client, ref, text, **opts)
            if not result.success:
                return result
            completion_tokens += result.completion_tokens
        return RunResult(ref=ref, success=True, completion_tokens=completion_tokens)

    @staticmethod
    def _write(text: str) -> None:
        """Write text to stdout without an implicit newline."""
        import sys

        sys.stdout.write(text)
        sys.stdout.flush()

    # --- device / status --------------------------------------------------

    def _detect_device(self) -> Device:
        """Best-effort device detection from LM Studio.

        LM Studio doesn't expose direct VRAM info via API, so we return
        UNKNOWN by default. Could be enhanced with system info if needed.
        """
        return Device.UNKNOWN


__all__ = ["LMStudioRuntime"]
