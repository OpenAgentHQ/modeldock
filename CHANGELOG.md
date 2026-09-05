# Changelog

All notable changes to ModelDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `registry_url` is now wired into discovery. Setting it under
  `catalog_source="auto"` merges a remote catalog ahead of every other source;
  `catalog_source="remote"` selects it as the only source (and errors when no
  `registry_url` is configured). The setting was previously parsed and
  displayed but never read.
- `RemoteRegistry` caches its fetch at `<cache_dir>/remote_catalog_cache.json`
  with a 1-hour TTL, served cache-first so a configured URL costs no network
  round-trip per command, and falls back to an expired cache before giving up.
  `refresh()` (and therefore `modeldock sources refresh`) bypasses the TTL.
- `catalog_entry_to_spec`/`load_bundled_catalog` (`adapters/registry/bundled.py`)
  — the catalog.json entry coercion, shared instead of reached for privately.

### Changed

- `RemoteRegistry` now merges remote entries *over* the bundled catalog rather
  than replacing it: a remote entry wins a name collision, but no bundled
  model is dropped, so a remote URL can only add to discovery.
- `RemoteRegistry` is built on `CachedCatalogRegistry`, so `search`,
  `recommend`, `by_category` and `list_all` answer from the merged index, and
  `get`/`resolve` honour aliases and casing like every other source.
- `CompositeRegistry.describe()` deduplicates sources by name, so a catalog
  merged inside more than one member is listed once by `modeldock sources`.

### Fixed

- `RemoteRegistry.search()`/`recommend()` delegated to the bundled fallback,
  so a model that existed only in the remote catalog could never be found —
  the exact case the remote catalog exists for.
- A successful remote fetch replaced the catalog instead of extending it,
  dropping every bundled model from `list_all()`/`by_category()`.
- `RemoteRegistry.get()` matched names exactly, ignoring aliases and casing.
- A single malformed entry in a remote payload discarded the entire fetch.
- `RemoteRegistry` exposed only a private `_refresh`, so `modeldock sources
  refresh` and `CompositeRegistry.refresh()` skipped it silently.
- `RemoteRegistry.describe()` reported the URL as its cache path, and reported
  the bundled fallback's model count as the remote source's when the fetch had
  failed.
- `RemoteRegistry` fetched on every construction with no cache, putting a
  network round-trip in front of every CLI invocation.
- `RemoteRegistry` accepted any URL scheme (including `file://`) and buffered
  the whole response body unbounded.

## [0.2.0] - 2026-08-28

Live GGUF catalogs, composite registry, third-party catalog plugins, and
llama.cpp runtime hardening.

### Added

- `Settings.llamacpp_gpu_layers` — configurable GPU layer offload count for
  llama-server, resolved via `config.toml`, then `MODELDOCK_LLAMACPP_GPU_LAYERS`,
  then llama-server's own `LLAMA_ARG_N_GPU_LAYERS`; `-1` means "offload all
  layers"; value is injected into the `-ngl` flag in launch command suggestions
- `LlamaCppRuntime(gpu_layers=...)` and `_resolve_runtime`/`RuntimeRegistry`
  wiring that forwards the configured value from `ModelManager`
- `CachedCatalogRegistry` (`adapters/registry/base.py`) — shared fetch →
  cache → index pipeline and `RegistryPort` implementation for live catalog
  sources
- `common/catalog_cache.py` — generic TTL'd JSON disk cache (extracted from
  `ollama_library.py`)
- `CatalogProvider` port (`ports/catalog_provider.py`) — the fetch/parse
  contract for live catalog sources
- `HuggingFaceCatalogProvider` (`adapters/registry/huggingface_catalog.py`) —
  live catalog that queries the Hugging Face Hub API (`filter=gguf`) for
  GGUF-format models, cached 24h; LM Studio and llama.cpp share one on-disk
  cache since both address the same GGUF universe
- `LlamaCppRuntime.models_for_category`/`models_for_capability` — llama.cpp
  previously had no catalog; category/capability installs fell back to the
  Ollama-tag catalog, whose names are not valid `--hf-repo` coordinates
- `CompositeRegistry` (`adapters/registry/composite.py`) — merges an ordered
  list of `RegistryPort` sources; earlier sources win on a name collision,
  `get()` returns the first source that resolves the reference
- `CatalogProviderRegistry` (`adapters/registry/catalog_registry.py`) —
  resolves a `RuntimeBackend` to its own live catalog: built-ins (Hugging
  Face for LM Studio/llama.cpp) plus third-party plugins discovered via the
  `modeldock.catalog_providers` entry-point group, mirroring how
  `RuntimeRegistry` discovers `modeldock.runtimes` plugins. A plugin is a
  callable `(cache_dir: Path) -> RegistryPort`; entry points take priority
  over built-ins, so a plugin can also replace the shipped Hugging Face provider

### Changed

- `OllamaLibraryRegistry` now builds on `CachedCatalogRegistry` instead of
  duplicating fetch/cache/index/`RegistryPort` logic inline; behavior unchanged
- `LMStudioRuntime.models_for_category`/`models_for_capability` now query the
  live Hugging Face catalog first, falling back to the curated
  `lmstudio_catalog.py` table only when the Hub is unreachable and no cache
  exists — suggestions still work fully offline, but may be a point-in-time
  list instead of the live one
- `LMStudioRuntime`/`LlamaCppRuntime` accept an optional `cache_dir` argument
  (defaults to the standard ModelDock cache directory)
- `ModelManager._resolve_registry` under `catalog_source="auto"` now merges
  the active backend's own live catalog with the general one when available —
  LM Studio/llama.cpp get a `CompositeRegistry` of
  `[HuggingFaceCatalogProvider, <ollama-or-bundled>]`, so `search()`/`list()`/
  `recommend()` surface models that backend can actually install. Ollama and
  backends without their own catalog are unaffected. `catalog_source="ollama"`
  / `"bundled"` remain explicit single-source opt-outs with no extra network
  calls
- `ModelManager._resolve_backend_catalog` now resolves through
  `CatalogProviderRegistry` instead of hardcoding `HuggingFaceCatalogProvider`
  — any backend with a registered catalog plugin is now picked up automatically

### Fixed

- `LlamaCppRuntime.list_installed()` no longer mis-parses Windows GGUF paths
  (`C:\models\model.gguf`) by splitting on the drive-letter colon
- `LlamaCppRuntime.is_installed()` now matches a bare GGUF filename (with or
  without `.gguf` extension) against the full path llama-server reports, so
  `run()`/`pull()`/`get_model_client()` no longer falsely report a loaded
  model as not installed

## [0.1.3] - 2026-07-19

Dynamic catalog: replaced static `catalog.json` with live scraping of ollama.com.

### Added

- `OllamaLibraryRegistry` adapter — scrapes `ollama.com/library` for the full model list, auto-detects categories and capabilities, and caches locally for offline use
- `catalog_source` config setting (`"auto"` | `"ollama"` | `"bundled"`) to control which registry is used
- `MODELDOCK_CATALOG_SOURCE` environment variable support
- Local catalog cache (`<cache_dir>/catalog_cache.json`) with 24-hour TTL

### Changed

- `ModelManager` now defaults to `OllamaLibraryRegistry` (dynamic) instead of `BundledRegistry` (static)
- Auto-detection rules: model name patterns and HTML capability tags determine `Category` and `Capability`
- `Architecture.md` updated to reflect dynamic catalog design

### Removed

- Deleted `src/modeldock/data/catalog.json` — no longer needed
- Removed `[tool.setuptools.package-data]` from `pyproject.toml`

### Deprecated

- `BundledRegistry` is now a fallback only, used when `catalog_source="bundled"` or when the dynamic catalog fails and no cache exists

### Tests

- 32 new tests for `OllamaLibraryRegistry` (HTML scraping, auto-detection, cache, network fallback)
- BundledRegistry tests skipped when `catalog.json` is not present

### Contributors

- @himanshu231204

---

## [0.1.2] - 2026-07-19

Patch fix for `catalog.json` not being included in the installed package.

### Fixed

- **Catalog data missing** — added `[tool.setuptools.package-data]` to `pyproject.toml` so `catalog.json` is bundled in the wheel/sdist. Previously the file was silently excluded, causing `ModelNotFoundError: 'catalog.json not found in package data'` at runtime.

---

## [0.1.1] - 2026-07-19

Patch release hardening the Ollama runtime and SDK ahead of broader adoption.

### Added

- `modeldock.run()` SDK entry point for single-prompt completions and an interactive REPL against the active runtime (#159)
- `RuntimePort.status()` reporting runtime availability and execution device (CPU/GPU), surfaced via `ModelManager.runtime_status()` and the `load` CLI (#11)
- `CachePort.path()` / `FilesystemCache.path()` / `CacheService.path()` returning the real cache directory (#158)
- `ModelSpec.from_ref` / `ModelInfo.from_ref` fallbacks so `load`/`info`/`install` work for installed models not present in the bundled catalog (#158)
- `PullResult.already_present` flag; `BaseRuntime.pull()` is now idempotent and skips re-downloading already-installed models (#161)
- `ModelRef.is_cloud` to identify cloud/subscription models (tag contains `cloud`)

### Changed

- SDK functions (`load`, `install`, `install_category`, `update`, `remove`, `verify`, `run`) now route the `backend` argument to the selected runtime (#159)
- `info()` surfaces installed tags for locally-installed models (#159)
- `ModelManager.update()` now requires `confirm=True` (it removes then re-downloads) and rejects cloud models (#160)
- `CachePort.clean()` / `FilesystemCache.clean()` / `CacheService.clean()` are safe by default (only corrupt/partial entries removed) and accept `force=True` to wipe all (#160)

### Fixed

- `OllamaRuntime.remove()` no longer hangs on cloud/subscription models; it short-circuits with a clear `DownloadError` (#160)
- Catalog fallback for `load`/`info`/`install` when a model is installed but absent from the bundled catalog (#158)

### Documentation

- README marks Ollama as fully supported; added author credit (#161)
- New `docs/ollama-sdk.md` SDK guide for using ModelDock with Ollama

### Contributors

- @himanshu231204

---

## [0.1.0] - 2026-07-18

Initial pre-release. Documentation and package skeleton only; no implementation
code yet.

### Added

- Project documentation set: `PROJECT.MD`, `Architecture.md`, `AGENT.md`, `QUICKSTART.md`, `Development.md`, `CONTEXT.md`, `INSTRUCTIONS.md`, `RELEASE.md`
- Package skeleton (`src/modeldock/`) following Clean Architecture: `domain`, `ports`, `core`, `adapters`, `cli`, `common`, `data`
- `pyproject.toml` with runtime/dev dependencies, `ollama`/`dev` extras, console script, and `modeldock.runtimes` entry point
- Public SDK surface (`modeldock`) and Typer-based CLI (`modeldock`) with Ollama runtime adapter
- GitHub release workflow (`.github/workflows/release.yml`) using `uv`, with 3-way version consistency check and PyPI publish
- PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
- Contributor community files: `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, issue templates, `CODEOWNERS`

### Changed

- Renamed `PROBLEM.MD` to `PROJECT.MD` (product intent doc)

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible new functionality
- **PATCH**: Backward-compatible bug fixes

## Links

[0.2.0]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/OpenAgentHQ/modeldock/releases/tag/v0.1.0
