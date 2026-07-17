# CONTEXT.md — ModelDock

Single-page orientation for humans and AI agents. Read this first; follow the
links for depth.

---

## What ModelDock Is

**A lightweight, Python-first model manager for local LLMs** — the "package
manager for local AI models." It discovers, downloads, caches, verifies, and
loads local models through pluggable runtime adapters. It does **not** run
inference itself; it orchestrates runtimes (starting with Ollama).

- **Repo:** https://github.com/OpenAgentHQ/modeldock.git
- **Language:** Python 3.9–3.12 · `src/` layout · pure-Python, minimal deps
- **Status:** Greenfield (docs only; no source yet)

---

## Document Map

| File | Purpose | Read when |
|---|---|---|
| `PROJECT.MD` | Product vision, pain points, goals, roadmap | Understanding *why* |
| `Architecture.md` | Design contract: layers, ports, modules, decisions | Designing/building |
| `AGENT.md` | Hard rules + workflow for agents/contributors | Writing code |
| `QUICKSTART.md` | 30-second user start (install, load, CLI) | Using it |
| `Development.md` | Env setup, build, test, CI, release | Contributing |
| `CONTEXT.md` | This file — orientation | Onboarding |

---

## Core Principles

1. **Management, not inference.** No torch/transformers. Runtime-native SDKs
   are optional extras only.
2. **Clean Architecture + SOLID + Dependency Inversion.** Dependencies point
   inward: `cli` → `core` → `ports` ← `adapters`; `domain`/`ports` are pure
   (no I/O, no framework, no Ollama/HTTP/fs references).
3. **Extensible by design.** New runtimes = one adapter class + one entry-point
   line. No core/CLI/API changes.
4. **Zero-config, beginner-friendly, cross-platform.** `platformdirs` for
   paths; works offline via bundled `catalog.json`.
5. **Typed errors, library-friendly logging.** Never `basicConfig()` at import;
   raise `ModelDockError` subclasses with actionable context.

---

## Architecture in One Breath

```
Interface:   modeldock/__init__.py (SDK)  +  modeldock/cli (Typer)
Application: modeldock/core/   (services, LifecycleOrchestrator, ModelManager)
Domain:      modeldock/domain/ (pure entities, no I/O)
Ports:       modeldock/ports/  (typing.Protocol interfaces)
Adapters:    modeldock/adapters/ (runtimes, registry, downloaders, cache, progress)
Common:      modeldock/common/ (config, logging, platform, http, errors)
Data:        modeldock/data/catalog.json (bundled model registry)
```

**Key ports:** `RuntimePort`, `RegistryPort`, `DownloaderPort`, `CachePort`,
`ProgressPort`, `EventPort`. Every adapter must pass the shared port-contract
test suite.

---

## Public API (shape)

```python
import modeldock as md
client = md.load("llama3")          # auto-install if missing → ready client
md.list()  md.search("coding")  md.installed()  md.info("qwen3")
md.install("llama3")  md.install_category("coding")
md.update("llama3")  md.remove("llama3")  md.verify("llama3")
md.cache.status()  md.cache.clean()
```

CLI mirrors this: `modeldock load|install|install-category|list|installed|
search|info|update|remove|cache|config`.

---

## Runtimes

| Runtime | Status |
|---|---|
| Ollama | ✅ Shipped (first) |
| LM Studio, llama.cpp, Jan AI, GPT4All, vLLM | 🔜 Planned adapters |

---

## Dependencies

Runtime: `typer`, `httpx`, `pydantic` (v2), `platformdirs`, `rich`, `tqdm`,
`tomli`/`tomllib`, `packaging`. Dev: `pytest`, `pytest-cov`, `pytest-mock`,
`ruff`, `mypy`, `bandit`, `pre-commit`.

---

## Agent / Contributor Rules (summary)

Full list in `AGENT.md`. Highlights:

- No code without an approved plan (discover → propose → approve → build).
- Keep `domain/` and `ports/` pure; depend inward only.
- New runtimes are adapters, never core edits.
- Cross-platform by default; no hardcoded paths or OS syscalls.
- Test in layers (unit / contract / integration / e2e); ≥80% coverage.

---

## Quick Links

- Install & start: see `QUICKSTART.md`
- Build & test: see `Development.md`
- Design rationale & trade-offs: see `Architecture.md` §16
- Vision & roadmap: see `PROJECT.MD`
