# Changelog

All notable changes to ModelDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

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

[0.1.3]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/OpenAgentHQ/modeldock/releases/tag/v0.1.0
