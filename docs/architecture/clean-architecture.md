# Clean Architecture

ModelDock follows Clean Architecture with SOLID principles. Dependencies point inward.

---

## Dependency Direction

```
cli → core → ports ← adapters
domain/ports import nothing from adapters/core/cli
```

This is non-negotiable. Violating it breaks extensibility and testability.

---

## The Layers

### Interface Layer (`modeldock/__init__.py` + `modeldock/cli`)

The public surface. The SDK exposes functions like `load()`, `list()`, `search()`. The CLI translates argv → core service calls.

**Rule:** No business logic in CLI. CLI only calls `core`.

---

### Application Layer (`modeldock/core/`)

Services that implement use cases by composing ports:

- `ModelManager` — high-level facade
- `LifecycleOrchestrator` — the brain behind `load()`
- `RegistryService` — search, info, categories
- `DownloadService` — orchestrates pull
- `CacheService` — smart caching
- `ConfigService` — settings

**Rule:** Depends on `ports/` interfaces only, never on concrete adapters.

---

### Domain Layer (`modeldock/domain/`)

Pure entities. No I/O, no framework imports, no references to Ollama/HTTP/filesystem.

- `Model`, `ModelSpec`, `ModelRef`
- `Capability`, `Category`
- `RuntimeBackend`
- `Alias`, alias resolution rules
- Domain exceptions

**Rule:** Validates invariants. Knows nothing about the outside world.

---

### Port Layer (`modeldock/ports/`)

`typing.Protocol` interfaces defining *what* the system needs:

- `RuntimePort` — runtime operations
- `RegistryPort` — model catalog
- `DownloaderPort` — file transfer
- `CachePort` — artifact tracking
- `ProgressPort` — progress reporting
- `EventPort` — lifecycle hooks

**Rule:** No implementation. Just the contract.

---

### Adapter Layer (`modeldock/adapters/`)

Concrete implementations of ports:

- `runtimes/ollama.py` — Ollama runtime (shipped)
- `runtimes/base.py` — shared logic (BaseRuntime)
- `registry/ollama_library.py` — dynamic catalog from ollama.com
- `registry/bundled.py` — offline fallback
- `downloaders/ollama_pull.py` — Ollama native pull
- `downloaders/http.py` — generic HTTP downloader
- `cache/filesystem.py` — filesystem cache + manifest
- `progress/rich_progress.py`, `tqdm_progress.py`, `silent.py`

**Rule:** Implements port interfaces. Registered via entry points.

---

### Common Layer (`modeldock/common/`)

Cross-cutting utilities:

- `config.py` — settings model + loaders
- `logging.py` — logging setup
- `platform.py` — OS detection, paths
- `http.py` — shared httpx client factory
- `errors.py` — base error hierarchy

**Rule:** No business logic. Pure utilities.

---

## Why This Matters

1. **Testability** — Core logic testable with fake adapters (no Ollama needed)
2. **Extensibility** — New runtimes = one adapter class + one entry-point line
3. **Independence** — Domain/ports have zero external dependencies
4. **Replaceability** — Swap any adapter without touching core

---

## Next Steps

- [Runtime Adapters](runtime-adapters.md) — adding new runtimes
- [Port Interfaces](ports.md) — the contract
