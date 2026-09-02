"""ModelManager — high-level facade over the core services.

Composes registry/runtime/cache/download/lifecycle into the public operations
(list, search, installed, info, install, install_category, update, remove,
verify, load, cache). This is what the SDK API and CLI both call. See
Architecture.md §5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, cast

from modeldock.adapters.downloaders.factory import needs_http_download
from modeldock.adapters.downloaders.http import HttpDownloader
from modeldock.adapters.progress import make_progress
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
from modeldock.domain.model import (
    Capability,
    Category,
    Device,
    ModelInfo,
    ModelRef,
    ModelSpec,
    RuntimeBackend,
    RuntimeStatus,
)
from modeldock.domain.source import SourceInfo, SourceTrust
from modeldock.ports.cache import CachePort, ContentStorePort
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
        # ``settings`` carries only the caller's deliberate overrides. Dumping it
        # whole would splash defaults for every unset field over the user's
        # config file as if they had been chosen, so
        # ``configure(log_level=...)`` would silently reset auto_install,
        # ollama_host and the rest. exclude_unset keeps the override sparse.
        self._config = config or ConfigService(
            explicit=settings.model_dump(exclude_unset=True) if settings else None
        )
        cfg = self._config.settings
        self._backend = backend or cfg.default_backend

        self._registry_port = registry or self._resolve_registry(cfg)
        self._runtime_registry = RuntimeRegistry()
        self._runtime = runtime or self._resolve_runtime(self._backend, cfg)

        self._cache_port = cache or self._default_cache(cfg)
        self._progress = make_progress(cfg.progress_style)

        self._registry = RegistryService(self._registry_port)
        self._cache = CacheService(self._cache_port)
        self._download = DownloadService(self._runtime, self._cache_port, self._progress)
        self._http_downloader = HttpDownloader()
        self._lifecycle = LifecycleOrchestrator(
            self._runtime,
            self._registry_port,
            self._cache_port,
            self._progress,
            events,
            auto_install=cfg.auto_install,
        )

    # --- resolution helpers ----------------------------------------------

    def _resolve_registry(self, cfg: Settings) -> RegistryPort:
        """Resolve which registry adapter to use based on catalog_source.

        Under ``"auto"``, the general catalog (Ollama live, falling back to
        bundled) is additionally merged with the active backend's own live
        catalog when it has one — LM Studio and llama.cpp are addressable
        through the Hugging Face Hub, not Ollama tags, so discovery
        (``search``/``list``/``recommend``) would otherwise surface names the
        active backend cannot actually install. ``"bundled"``/``"ollama"``
        stay single-source and network-free/live-only respectively, exactly
        as before — they are explicit opt-outs of this merge.
        """
        source = cfg.catalog_source
        if source == "bundled":
            from modeldock.adapters.registry.bundled import BundledRegistry

            return BundledRegistry()
        elif source == "ollama":
            from modeldock.adapters.registry.ollama_library import OllamaLibraryRegistry

            return OllamaLibraryRegistry(cache_dir=cfg.cache_dir)
        else:  # "auto" — try ollama, fallback to bundled; merge in a backend catalog
            base = self._resolve_auto_registry(cfg)
            backend_catalog = self._resolve_backend_catalog(cfg)
            if backend_catalog is None:
                return base
            from modeldock.adapters.registry.composite import CompositeRegistry

            return CompositeRegistry([backend_catalog, base])

    def _resolve_auto_registry(self, cfg: Settings) -> RegistryPort:
        """The general catalog for ``"auto"``: live Ollama, falling back to bundled."""
        from modeldock.adapters.registry.bundled import BundledRegistry

        try:
            from modeldock.adapters.registry.ollama_library import OllamaLibraryRegistry

            live = OllamaLibraryRegistry(cache_dir=cfg.cache_dir)
        except Exception as exc:
            self._logger.debug("Live catalog unavailable (%s); using bundled", exc)
            return BundledRegistry()
        # The live registry swallows network errors and constructs with an
        # empty index when there is neither network nor cache, so an
        # exception is not the only failure mode we must fall back from.
        if not live.list_all():
            self._logger.info("Live catalog empty; falling back to the bundled catalog")
            return BundledRegistry()
        return live

    def _resolve_backend_catalog(self, cfg: Settings) -> Optional[RegistryPort]:
        """The active backend's own live catalog, or None when it has none.

        Resolved through ``CatalogProviderRegistry``, which knows the
        built-in mapping (Hugging Face for LM Studio/llama.cpp) and discovers
        third-party ``modeldock.catalog_providers`` plugins for any other
        backend — a package can add live discovery for a new runtime without
        any change to ModelDock itself. Failures (no network, no cache, no
        catalog for this backend at all) all degrade to None rather than
        raising, exactly like the general catalog's own fallback.
        """
        from modeldock.adapters.registry.catalog_registry import CatalogProviderRegistry

        return CatalogProviderRegistry().get(self._backend, cfg.cache_dir)

    #: Config field holding the host override for each backend that has one.
    _HOST_SETTING_FOR = {
        RuntimeBackend.OLLAMA: "ollama_host",
        RuntimeBackend.LM_STUDIO: "lmstudio_host",
    }

    #: Config field holding the GPU-layers override for each backend that has one.
    _GPU_LAYERS_SETTING_FOR = {
        RuntimeBackend.LLAMACPP: "llamacpp_gpu_layers",
    }

    #: Config field holding the local model directory for file-based runtimes.
    _MODELS_DIR_SETTING_FOR = {
        RuntimeBackend.GPT4ALL: "gpt4all_models_dir",
    }

    def _resolve_runtime(self, backend: RuntimeBackend, cfg: Settings) -> RuntimePort:
        # Apply the configured host at construction time so it always takes
        # effect (clients are built lazily and cached per instance). Backends
        # with no configured host resolve their own, discovering it when the
        # server is not on the conventional address.
        host_field = self._HOST_SETTING_FOR.get(backend)
        host = getattr(cfg, host_field, None) if host_field else None
        gpu_layers_field = self._GPU_LAYERS_SETTING_FOR.get(backend)
        gpu_layers = getattr(cfg, gpu_layers_field, None) if gpu_layers_field else None
        models_dir_field = self._MODELS_DIR_SETTING_FOR.get(backend)
        models_dir = getattr(cfg, models_dir_field, None) if models_dir_field else None
        try:
            runtime = self._runtime_registry.get(
                backend,
                host=host,
                gpu_layers=gpu_layers,
                models_dir=models_dir,
            )
        except KeyError as exc:
            raise RuntimeUnavailableError(backend.value) from exc
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

    def runtimes(self) -> List[RuntimeStatus]:
        """Report every registered runtime backend and its current status.

        Backs ``modeldock runtimes``. Probes each built-in and entry-point
        backend so users can see which runtimes are reachable without
        switching ``--backend`` one at a time. A backend that fails to probe
        is reported as unavailable with the reason in ``details`` rather than
        dropped from the list, so a broken plugin never hides the rest.
        """
        statuses: List[RuntimeStatus] = []
        backends = sorted(self._runtime_registry.available_backends(), key=lambda b: b.value)
        for backend in backends:
            try:
                statuses.append(self._runtime_registry.get(backend).status())
            except Exception as exc:  # noqa: BLE001 - one bad adapter must not hide the others
                self._logger.warning("Runtime %s failed to report status: %s", backend.value, exc)
                statuses.append(
                    RuntimeStatus(
                        backend=backend,
                        available=False,
                        device=Device.UNKNOWN,
                        details=f"probe failed: {exc}",
                    )
                )
        return statuses

    def recommend(self, task: str) -> List[Any]:
        """Recommend models for a task."""
        return self._registry.recommend(task)

    def resolve(self, name: str) -> ModelSpec:
        """Resolve a friendly name/alias to its canonical catalog spec.

        Surfaces the "friendly name → canonical identity" step of the
        discovery flow, including which source the model came from
        (``spec.source``). Raises ``ModelNotFoundError`` when unknown.
        """
        resolver = getattr(self._registry_port, "resolve", self._registry_port.get)
        return resolver(ModelRef.parse(name))

    def versions(self, name: str) -> List[str]:
        """Return the known version tags a source exposes for ``name``."""
        ref = ModelRef.parse(name)
        versions = getattr(self._registry_port, "versions", None)
        if callable(versions):
            return cast(List[str], versions(ref))
        try:
            return self._registry_port.get(ref).version_tags()
        except ModelNotFoundError:
            return []

    # --- sources / observability ----------------------------------------

    def sources(self) -> List[SourceInfo]:
        """Describe the active model sources feeding discovery.

        Backs ``modeldock sources``. Reports every source in the resolved
        registry (a ``CompositeRegistry`` fans out to its members) so users
        can see where discovered models come from and whether each source is
        currently populated.
        """
        describe = getattr(self._registry_port, "describe", None)
        if callable(describe):
            return list(describe())
        # A source predating the describe() contract still counts as one source.
        return [
            SourceInfo(
                name=type(self._registry_port).__name__,
                trust=SourceTrust.CUSTOM,
                live=True,
                model_count=len(self._registry_port.list_all()),
            )
        ]

    def refresh_sources(self) -> List[SourceInfo]:
        """Force each live source to re-fetch, bypassing its cache TTL.

        Backs ``modeldock sources refresh``. Returns the post-refresh source
        descriptors so callers can report the new model counts.
        """
        refresh = getattr(self._registry_port, "refresh", None)
        if callable(refresh):
            refresh()
        return self.sources()

    # --- lifecycle ------------------------------------------------------

    def load(self, name: str, auto_install: Optional[bool] = None) -> Any:
        """Resolve, ensure installed, verify, return a ready client."""
        return self._lifecycle.load(name, auto_install=auto_install)

    def install(self, name: str, auto_install: bool = True) -> ModelRef:
        """Explicitly download/install a model."""
        ref = ModelRef.parse(name, backend=self._backend)
        # Resolve the spec to decide which download path to use.
        # Allow locally-known models absent from the catalog (pulled outside
        # ModelDock) by catching ModelNotFoundError instead of raising.
        spec: Optional[ModelSpec] = None
        try:
            spec = self._registry_port.get(ref)
        except ModelNotFoundError:
            if not self._runtime.is_installed(ref):
                raise

        if spec is not None and needs_http_download(spec):
            self._install_via_http(spec, ref)
        else:
            self._download.pull(ref)
        return ref

    def _install_via_http(self, spec: ModelSpec, ref: ModelRef) -> None:
        """Fetch a raw artifact into the content-addressed cache.

        Weights are keyed by SHA-256, so two refs resolving to byte-identical
        files share one copy on disk instead of one copy each. When the catalog
        publishes the digest and those bytes are already stored, the download is
        skipped outright — the re-install is instant and works offline.
        Caches that do not store blobs keep the previous download-to-path
        behaviour.
        """
        dest = self._model_dest(spec, ref)
        variant = spec.default_variant()
        expected = (variant.sha256 or "").strip().lower() if variant else ""

        store: Optional[ContentStorePort] = None
        if isinstance(self._cache_port, ContentStorePort):
            store = self._cache_port
        if store is None:
            self._http_downloader.download(spec, dest, self._progress)
            self._cache_port.record(
                ref=ref,
                tag=ref.tag,
                sha256=expected,
                size_bytes=dest.stat().st_size,
            )
            return

        if expected and store.has_blob(expected):
            self._logger.info(
                "Reusing cached weights for %s (sha256 %s)", ref.qualified_name(), expected[:12]
            )
            blob, digest = store.blob_path(expected), expected
        else:
            self._http_downloader.download(spec, dest, self._progress)
            blob, digest = store.store_blob(dest, expected or None)
        store.link_into(blob, dest)
        store.record_artifact(
            ref=ref,
            tag=ref.tag,
            sha256=digest,
            size_bytes=blob.stat().st_size,
            path=dest,
        )

    def _model_dest(self, spec: ModelSpec, ref: ModelRef) -> Path:
        """Filesystem path for an HTTP-downloaded GGUF artifact."""
        cache_dir: Path = self._config.settings.cache_dir
        return cache_dir / "models" / spec.name / f"{ref.tag}.gguf"

    def suggest_category(self, category: str) -> List[ModelRef]:
        """Return the models ``install_category`` would install, without installing.

        Prefers the active runtime's own mapping when it has one. The shared
        catalog is built from Ollama tags, which are not valid identifiers on
        every backend — LM Studio addresses models by Hugging Face coordinates
        — so a runtime that names models differently supplies its own list.
        Runtimes without a mapping fall back to the catalog unchanged.
        """
        cat = Category.from_value(category)
        # ``or []`` guards adapters that inherit the Protocol's stub body,
        # which returns None rather than an empty list.
        backend_refs = self._runtime.models_for_category(cat) or []
        if backend_refs:
            return list(backend_refs)
        return [
            ModelRef.parse(spec.name, backend=self._backend)
            for spec in self._registry.by_category(cat)
        ]

    def suggest_capability(self, capability: str) -> List[ModelRef]:
        """Return models exposing ``capability``, preferring the runtime's mapping."""
        cap = Capability.from_value(capability)
        backend_refs = self._runtime.models_for_capability(cap) or []
        if backend_refs:
            return list(backend_refs)
        return [
            ModelRef.parse(spec.name, backend=self._backend)
            for spec in self._registry.list_all()
            if cap in spec.capabilities
        ]

    def install_category(self, category: str) -> List[ModelRef]:
        """Bulk-install every model in a category.

        Resolves through ``suggest_category``, so each backend installs models
        it can actually pull.
        """
        targets = self.suggest_category(category)
        if not targets:
            raise ModelNotFoundError(f"{category} (category, backend {self._backend.value})")
        refs: List[ModelRef] = []
        for ref in targets:
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
        user_cfg = self._cache_port.get_model_config(ref)
        self._runtime.remove(ref)
        self._download.pull(ref)
        if user_cfg is not None:
            self._cache_port.set_model_config(ref, user_cfg)
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
