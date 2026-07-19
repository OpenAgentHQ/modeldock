"""ModelManager — high-level facade over the core services.

Composes registry/runtime/cache/download/lifecycle into the public operations
(list, search, installed, info, install, install_category, update, remove,
verify, load, cache). This is what the SDK API and CLI both call. See
Architecture.md §5.
"""

from __future__ import annotations

from typing import Any, List, Optional

from modeldock.adapters.progress import make_progress
from modeldock.adapters.registry import BundledRegistry
from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.common.config import Settings
from modeldock.common.errors import (
    DownloadError,
    ModelNotFoundError,
    RuntimeUnavailableError,
)
from modeldock.common.logging import get_logger
from modeldock.core.cache import CacheService
from modeldock.core.config import ConfigService
from modeldock.core.download import DownloadService
from modeldock.core.lifecycle import LifecycleOrchestrator
from modeldock.core.registry import RegistryService
from modeldock.domain.model import Category, ModelInfo, ModelRef, RuntimeBackend
from modeldock.ports.cache import CachePort
from modeldock.ports.events import EventPort
from modeldock.ports.registry import RegistryPort
from modeldock.ports.runtime import RuntimePort


class ModelManager:
    """Facade coordinating all model-management operations."""

    def __init__(
        self,
        backend: Optional[RuntimeBackend] = None,
        config: Optional[ConfigService] = None,
        registry: Optional[RegistryPort] = None,
        runtime: Optional[RuntimePort] = None,
        cache: Optional[CachePort] = None,
        events: Optional[EventPort] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._logger = get_logger("core.manager")
        self._config = config or ConfigService(explicit=settings.model_dump() if settings else None)
        cfg = self._config.settings
        self._backend = backend or cfg.default_backend

        self._registry_port = registry or BundledRegistry()
        self._runtime_registry = RuntimeRegistry()
        self._runtime = runtime or self._resolve_runtime(self._backend, cfg)

        self._cache_port = cache or self._default_cache(cfg)
        self._progress = make_progress(cfg.progress_style)

        self._registry = RegistryService(self._registry_port)
        self._cache = CacheService(self._cache_port)
        self._download = DownloadService(self._runtime, self._cache_port, self._progress)
        self._lifecycle = LifecycleOrchestrator(
            self._runtime,
            self._registry_port,
            self._cache_port,
            self._progress,
            events,
            auto_install=cfg.auto_install,
        )

    # --- resolution helpers ----------------------------------------------

    def _resolve_runtime(self, backend: RuntimeBackend, cfg: Settings) -> RuntimePort:
        try:
            runtime = self._runtime_registry.get(backend)
        except KeyError as exc:
            raise RuntimeUnavailableError(backend.value) from exc
        # Apply the configured host at construction time so it always takes
        # effect (the Ollama client is built lazily and cached per instance).
        if backend == RuntimeBackend.OLLAMA and cfg.ollama_host:
            runtime = self._runtime_registry.get(backend, host=cfg.ollama_host)
        if not runtime.is_available():
            self._logger.warning("Runtime %s not available", backend.value)
        return runtime

    def _default_cache(self, cfg: Settings) -> CachePort:
        from modeldock.adapters.cache import FilesystemCache

        return FilesystemCache(cfg.cache_dir)

    # --- discovery ------------------------------------------------------

    def list(self) -> List[Any]:
        """List all known models in the catalog."""
        return self._registry.list_all()

    def search(self, query: str) -> List[Any]:
        """Search the catalog by name/alias/capability/category."""
        return self._registry.search(query)

    def installed(self) -> List[ModelRef]:
        """Return models present locally in the active runtime."""
        return self._runtime.list_installed()

    def info(self, name: str) -> Any:
        """Return metadata for a model, including installed tags/versions.

        Surfaces the concrete tags present in the active runtime (issue #10) by
        intersecting the runtime's installed refs with this model's name. When
        the model is not in the bundled catalog but is installed locally, falls
        back to a minimal ``ModelInfo`` built from the local reference.
        """
        ref = ModelRef.parse(name)
        installed_tags = [
            existing.tag for existing in self._runtime.list_installed() if existing.name == ref.name
        ]
        try:
            return self._registry.info(name, installed_tags=installed_tags)
        except ModelNotFoundError:
            # Fall back only for models that are actually installed locally but
            # absent from the bundled catalog; otherwise surface the error.
            if installed_tags:
                return ModelInfo.from_ref(ref, installed_tags)
            raise

    def categories(self) -> List[Category]:
        """Return all catalog categories."""
        return self._registry.categories()

    def runtime_status(self) -> Any:
        """Report the active runtime's availability and execution device."""
        return self._runtime.status()

    def recommend(self, task: str) -> List[Any]:
        """Recommend models for a task."""
        return self._registry.recommend(task)

    # --- lifecycle ------------------------------------------------------

    def load(self, name: str, auto_install: Optional[bool] = None) -> Any:
        """Resolve, ensure installed, verify, return a ready client."""
        return self._lifecycle.load(name, auto_install=auto_install)

    def install(self, name: str, auto_install: bool = True) -> ModelRef:
        """Explicitly download/install a model."""
        ref = ModelRef.parse(name, backend=self._backend)
        # Validate against the catalog, but allow locally-known models that are
        # absent from the bundled catalog (e.g. pulled outside ModelDock).
        try:
            self._registry.info(name)
        except ModelNotFoundError:
            if not self._runtime.is_installed(ref):
                raise
        self._download.pull(ref)
        return ref

    def install_category(self, category: str) -> List[ModelRef]:
        """Bulk-install every model in a category."""
        cat = Category.from_value(category)
        refs: List[ModelRef] = []
        for spec in self._registry.by_category(cat):
            ref = ModelRef.parse(spec.name, backend=self._backend)
            self._download.pull(ref)
            refs.append(ref)
        return refs

    def update(self, name: str, confirm: bool = False) -> ModelRef:
        """Pull a newer tag for an installed model.

        Destructive: removes the current copy and re-downloads. Requires
        ``confirm=True`` to proceed, so a large model is never re-pulled by
        accident. Cloud/subscription models cannot be updated locally.
        """
        ref = ModelRef.parse(name, backend=self._backend)
        if ref.is_cloud:
            raise DownloadError(
                ref.name,
                reason=(
                    f"{ref.qualified_name()} is a cloud/subscription model and "
                    "cannot be updated locally."
                ),
            )
        if not self._runtime.is_installed(ref):
            raise ModelNotFoundError(name)
        if not confirm:
            raise DownloadError(
                ref.name,
                reason=(
                    f"update() removes and re-downloads {ref.qualified_name()}. "
                    "Pass confirm=True to proceed."
                ),
            )
        self._runtime.remove(ref)
        self._download.pull(ref)
        return ref

    def remove(self, name: str) -> None:
        """Uninstall a model from the runtime."""
        ref = ModelRef.parse(name, backend=self._backend)
        self._runtime.remove(ref)

    def run(self, name: str, prompt: Optional[str] = None, **opts: Any) -> Any:
        """Run an interactive session for a model in the active runtime."""
        ref = ModelRef.parse(name, backend=self._backend)
        return self._runtime.run(ref, prompt=prompt, **opts)

    def verify(self, name: str) -> bool:
        """Verify a model is installed in the runtime."""
        ref = ModelRef.parse(name, backend=self._backend)
        return self._download.verify(ref)

    # --- cache ----------------------------------------------------------

    @property
    def cache(self) -> CacheService:
        """Expose the cache service (status/clean/path)."""
        return self._cache


__all__ = ["ModelManager"]
