# Overview

ModelDock is a lightweight, Python-first model management layer for local LLM runtimes — the "package manager for local AI models."

---

## What ModelDock Does

It manages discovery, download, caching, installation verification, and loading through pluggable runtime adapters. It does **not** run inference itself; it orchestrates runtimes (starting with Ollama).

---

## Core Concept: The `load()` Flow

The flagship operation:

<div class="flow-diagram" markdown>
Model requested
    |
Already installed? ──yes──> return client
    | no
Download automatically (with progress)
    |
Verify installation (checksum + runtime check)
    |
Load model -> return ready client
</div>

---

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Auto-install** | `load()` downloads missing models automatically |
| **Searchable catalog** | Browse models, categories, capabilities from Python |
| **Bulk install** | `install_category("coding")` pulls related models |
| **Smart caching** | Never re-download installed models |
| **Runtime adapters** | Ollama now, LM Studio/llama.cpp/vLLM later |
| **Cross-platform** | Windows, macOS, Linux via `platformdirs` |
| **Zero-config** | Dynamic catalog from ollama.com with offline fallback |

---

## Architecture Layers

ModelDock follows **Clean Architecture** with SOLID principles:

| Layer | Location | Purpose |
|-------|----------|---------|
| **Interface** | `modeldock/__init__.py` + `modeldock/cli` | SDK and CLI |
| **Application** | `modeldock/core/` | Services, orchestrator, manager |
| **Domain** | `modeldock/domain/` | Pure entities, no I/O |
| **Ports** | `modeldock/ports/` | Protocol interfaces |
| **Adapters** | `modeldock/adapters/` | Runtimes, registry, downloaders |
| **Common** | `modeldock/common/` | Config, logging, errors |

Dependencies point inward: `cli → core → ports ← adapters`.

---

## Next Steps

- [Discover Models](discover.md) — browse and search the catalog
- [Install & Manage](install.md) — manage model lifecycle
- [Load & Run](load.md) — load models and run completions
- [Configuration](configuration.md) — customize behavior
