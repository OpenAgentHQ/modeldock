"""LlamaCppRuntime — runtime adapter for llama.cpp's server (llama-server).

Implements ``RuntimePort`` against the OpenAI-compatible HTTP API exposed by
``llama-server`` at http://localhost:8080 (default). Unlike Ollama and LM
Studio, llama-server binds exactly one GGUF model per process and has no
network API to download, swap, or unload models, so ``pull``/``remove``
return clear, actionable guidance instead of pretending to manage a remote
catalog. See Architecture.md §4/§14.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.common.errors import (
    DownloadError,
    ModelDockError,
    ModelNotInstalledError,
    RuntimeUnavailableError,
)
from modeldock.domain.model import Capability, Category, Device, ModelRef, RuntimeBackend
from modeldock.ports.runtime import PullResult, RunResult

if TYPE_CHECKING:
    from modeldock.adapters.registry.huggingface_catalog import HuggingFaceCatalogProvider

_DEFAULT_HOST = "http://localhost:8080"
_DEFAULT_TIMEOUT = 30.0

# llama.cpp has no vendor-standard client-discovery env var (unlike Ollama's
# OLLAMA_HOST or LM Studio's LM_STUDIO_HOST), so both names here are
# ModelDock's own convention: the namespaced form takes precedence.
_HOST_ENV_VARS = ("MODELDOCK_LLAMACPP_HOST", "LLAMACPP_HOST")

# Probed in order when no host is configured (see the LM Studio adapter for
# why each address is here).
_HOST_CANDIDATES = (
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://host.docker.internal:8080",
)

# /health is llama-server's lightweight liveness endpoint: present as soon as
# the process is up, even while the model is still loading.
_PROBE_PATH = "/health"

_SERVER_NOT_RUNNING_HINT = "Start llama.cpp's server: `llama-server -m <model.gguf>`."
_SINGLE_MODEL_HINT = (
    "llama-server binds exactly one model per process and exposes no API to "
    "download or swap models. Stop the server and restart it with "
    "`llama-server -m <model.gguf>` (or `--hf-repo`/`--hf-file` to fetch from "
    "Hugging Face) pointing at the model you want."
)


class LlamaCppRuntime(BaseRuntime):
    """Runtime adapter for llama.cpp's server (llama-server)."""

    backend: RuntimeBackend = RuntimeBackend.LLAMACPP

    def __init__(
        self,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self._host = host
        self._api_key = api_key
        self._client: Any = None
        self._cache_dir = cache_dir
        self._hf_catalog: Optional[HuggingFaceCatalogProvider] = None

    # --- internal helpers -------------------------------------------------

    def _resolve_host(self) -> str:
        """Resolve the server base URL.

        Precedence: explicit arg (config) > MODELDOCK_LLAMACPP_HOST >
        LLAMACPP_HOST > auto-discovery across the known local addresses >
        ``http://localhost:8080``. See ``BaseRuntime.resolve_host``.
        """
        return self.resolve_host(
            explicit=self._host,
            env_vars=_HOST_ENV_VARS,
            default=_DEFAULT_HOST,
            candidates=_HOST_CANDIDATES,
            probe_path=_PROBE_PATH,
        )

    def _resolve_api_key(self) -> Optional[str]:
        """API key precedence: explicit arg > LLAMACPP_API_KEY env > None."""
        import os

        return self._api_key or os.environ.get("LLAMACPP_API_KEY")

    def _ensure_client(self) -> Any:
        """Lazily build an OpenAI-compatible client for llama-server."""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeUnavailableError(
                "llamacpp",
                hint="Install the OpenAI SDK with `pip install openai`.",
            ) from exc
        try:
            api_key = self._resolve_api_key() or "llama-cpp"
            self._client = OpenAI(
                base_url=f"{self._resolve_host()}/v1",
                api_key=api_key,
                timeout=_DEFAULT_TIMEOUT,
            )
        except Exception as exc:
            raise RuntimeUnavailableError(
                "llamacpp",
                hint=f"Failed to build llama.cpp client: {exc}",
            ) from exc
        return self._client

    def _ensure_http_client(self) -> Any:
        """Build an httpx client for native llama-server API calls."""
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
        """True if llama-server is reachable and healthy."""
        try:
            http_client = self._ensure_http_client()
            response = http_client.get("/health")
            return bool(response.status_code == 200)
        except Exception:
            return False

    def _require_available(self) -> None:
        """Raise a clear, typed error if llama-server isn't reachable.

        ``list_installed``/``_check_available`` degrade to False/[] on a down
        server so read-only status checks stay quiet, but operations that
        actually need the server (run, remove) must fail loudly instead of
        surfacing a misleading downstream error like "model not installed".
        """
        if not self.is_available():
            raise RuntimeUnavailableError("llamacpp", hint=_SERVER_NOT_RUNNING_HINT)

    # --- backend-specific model suggestions --------------------------------

    def _live_catalog(self) -> HuggingFaceCatalogProvider:
        """Return the lazily-built, memoized live Hugging Face catalog.

        Constructed once per runtime instance since it fetches over the
        network on first use (like ``OllamaLibraryRegistry``).
        """
        if self._hf_catalog is None:
            from modeldock.adapters.registry.huggingface_catalog import (
                HuggingFaceCatalogProvider,
            )
            from modeldock.common.platform import default_cache_dir

            self._hf_catalog = HuggingFaceCatalogProvider(
                self._cache_dir or default_cache_dir(), RuntimeBackend.LLAMACPP
            )
        return self._hf_catalog

    def models_for_category(self, category: Category) -> List[ModelRef]:
        """Return llama.cpp-addressable models for ``category``.

        llama.cpp has no catalog of its own: it loads GGUF files directly, and
        can fetch them straight from a Hugging Face repo via ``--hf-repo`` (see
        ``_SINGLE_MODEL_HINT``). The shared Ollama-scraped catalog names are not
        valid ``--hf-repo`` coordinates, so category installs resolve through
        the live Hugging Face GGUF listing instead. Returns an empty list
        (rather than the wrong names) when the Hub is unreachable and no cache
        exists yet.
        """
        return self._live_catalog().models_for_category(category)

    def models_for_capability(self, capability: Capability) -> List[ModelRef]:
        """Return llama.cpp-addressable models exposing ``capability`` (live)."""
        return self._live_catalog().models_for_capability(capability)

    def _parse_model_id(self, entry: Any) -> str:
        """Extract a model ID from a /v1/models entry (object or dict)."""
        if hasattr(entry, "id"):
            return str(entry.id)
        if isinstance(entry, dict):
            return str(entry.get("id", ""))
        return ""

    # --- RuntimePort hooks ------------------------------------------------

    def list_installed(self) -> List[ModelRef]:
        """Return the model currently loaded by llama-server.

        llama-server binds exactly one GGUF model per process, so this is at
        most a single-element list. Queries /v1/models. Returns an empty list
        if the server is unreachable (expected offline state).
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
            refs.append(ModelRef.parse(model_id, backend=RuntimeBackend.LLAMACPP))
        return refs

    def _do_pull(self, ref: ModelRef, progress: Any) -> PullResult:
        """Fail clearly: llama-server has no API to download or swap models.

        Unlike Ollama/LM Studio, llama.cpp's server does not manage a remote
        model catalog it can pull into — it only ever serves the GGUF file it
        was started with. Report this plainly instead of pretending to
        download, so callers get an actionable message rather than a silent
        no-op.
        """
        if progress is not None:
            progress.start(total=0, desc=f"Pulling {ref.qualified_name()}")
            progress.finish(desc=f"Pull not supported for {ref.qualified_name()}")
        return PullResult(
            ref=ref,
            success=False,
            error=f"llama.cpp does not support remote pull. {_SINGLE_MODEL_HINT}",
        )

    def _get_client(self, ref: ModelRef) -> Any:
        """Return an OpenAI-compatible client for the model."""
        return self._ensure_client()

    def remove(self, ref: ModelRef) -> None:
        """Not supported: llama-server has no API to unload or delete a model."""
        if ref.is_cloud:
            raise DownloadError(
                ref.name,
                reason=(
                    f"{ref.qualified_name()} is a cloud/subscription model and "
                    "cannot be removed locally."
                ),
            )
        self._require_available()
        raise DownloadError(ref.name, reason=_SINGLE_MODEL_HINT)

    def run(
        self,
        ref: ModelRef,
        prompt: Optional[str] = None,
        **opts: Any,
    ) -> RunResult:
        """Run an interactive session, streaming tokens to stdout.

        When ``prompt`` is given, runs a single completion and returns. When
        ``prompt`` is ``None``, drops into a read-eval-print loop reading lines
        from stdin until EOF or a quit command. Requires the model to be the
        one currently loaded by llama-server.
        """
        self._require_available()
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
        """llama-server exposes no device metadata via its HTTP API.

        GPU offload is a compile-time/CLI concern (``-ngl``) on llama.cpp, not
        something the server reports back, so we cannot infer it here.
        """
        return Device.UNKNOWN


__all__ = ["LlamaCppRuntime"]
