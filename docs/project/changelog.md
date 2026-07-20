# Changelog

All notable changes to ModelDock.

Based on [Keep a Changelog](https://keepachangelog.com/) and [Semantic Versioning](https://semver.org/).

---

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

### Removed

- Deleted `src/modeldock/data/catalog.json` — no longer needed

### Tests

- 32 new tests for `OllamaLibraryRegistry`

---

## [0.1.2] - 2026-07-19

Patch fix for `catalog.json` not being included in the installed package.

### Fixed

- **Catalog data missing** — added `[tool.setuptools.package-data]` to `pyproject.toml`

---

## [0.1.1] - 2026-07-19

Patch release hardening the Ollama runtime and SDK.

### Added

- `modeldock.run()` SDK entry point for single-prompt completions and interactive REPL
- `RuntimePort.status()` reporting runtime availability and execution device
- `CachePort.path()` / `FilesystemCache.path()` / `CacheService.path()` returning the real cache directory
- `ModelSpec.from_ref` / `ModelInfo.from_ref` fallbacks for installed models not in catalog
- `PullResult.already_present` flag; `BaseRuntime.pull()` is now idempotent
- `ModelRef.is_cloud` to identify cloud/subscription models

### Changed

- SDK functions now route the `backend` argument to the selected runtime
- `info()` surfaces installed tags for locally-installed models
- `ModelManager.update()` now requires `confirm=True`
- `CachePort.clean()` are safe by default and accept `force=True`

### Fixed

- `OllamaRuntime.remove()` no longer hangs on cloud/subscription models
- Catalog fallback for `load`/`info`/`install` when model is installed but absent from bundled catalog

---

## [0.1.0] - 2026-07-18

Initial pre-release. Documentation and package skeleton only.

### Added

- Project documentation set
- Package skeleton following Clean Architecture
- `pyproject.toml` with runtime/dev dependencies
- Public SDK surface and Typer-based CLI
- GitHub release workflow
- Contributor community files

---

## Links

[0.1.3]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/OpenAgentHQ/modeldock/releases/tag/v0.1.0
