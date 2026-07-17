# AGENT.md — ModelDock

Guidance for AI coding agents and contributors working in this repository.

ModelDock is a **lightweight, Python-first model management layer for local LLM
runtimes** — the "package manager for local AI models." It manages discovery,
download, caching, installation verification, and loading. It does **not** run
inference itself; it orchestrates runtimes (starting with Ollama).

Read [`PROJECT.MD`](./PROJECT.MD) for the full vision and pain points, and
[`Architecture.md`](./Architecture.md) for the authoritative design contract
before writing any code.

---

## Project Snapshot

- **Language:** Python 3.10+ (type hints on all public functions)
- **Packaging:** `src/` layout, `pyproject.toml`, pure-Python, minimal deps
- **First runtime:** Ollama (shipped). Future: LM Studio, llama.cpp, Jan AI,
  GPT4All, vLLM (added as adapters, no core changes)
- **Design style:** Clean Architecture + SOLID + Dependency Inversion
- **Status:** Greenfield. No source code yet — only docs (`PROJECT.MD`,
  `Architecture.md`, `README.md`, `LICENSE`).

---

## Hard Rules (must not violate)

1. **No implementation without approved plan.** Follow the workflow: discover →
   propose → approve → init session → plan → execute → validate. Nothing is
   written to disk until the user approves the approach.
2. **Domain and ports stay pure.** `modeldock/domain/` and `modeldock/ports/`
   must contain NO I/O, NO framework imports, NO references to Ollama/HTTP/fs.
   They define *what* is needed; adapters provide *how*.
3. **Depend inward only.** `core/` depends on `ports/` interfaces, never on
   concrete adapters. Adapters depend on ports. Nothing in `domain`/`ports`
   imports from `adapters`/`core`/`cli`.
4. **New runtimes are adapters, not core edits.** Adding LM Studio / llama.cpp /
   Jan / GPT4All / vLLM = one new class in `modeldock/adapters/runtimes/`
   implementing `RuntimePort` + one entry-point line in `pyproject.toml`. Do NOT
   modify `ModelManager`, `LifecycleOrchestrator`, or the public API.
5. **No heavy ML deps.** Do not add torch/transformers/etc. ModelDock manages
   models; it does not infer. Runtime-native SDKs (e.g. `ollama`) are optional
   extras only.
6. **Library-friendly logging.** Never call `logging.basicConfig()` at import
   time. Use the `modeldock.*` named logger; configure only in CLI/entry points.
7. **Typed errors, never silent swallows.** Raise `ModelDockError` subclasses
   (see `common/errors.py`). Every error must carry actionable context.
 8. **Cross-platform by default.** Use `platformdirs` for paths, avoid
    hardcoded `/` or `C:\`, avoid OS-specific syscalls without guards.

---

## Coding Standards

- **Python 3.10+**, type hints on **all** public functions (and prefer them
  elsewhere). `mypy --strict` must pass.
- **Pydantic v2** for all data models (config, model specs, registry entries).
- **Naming:** `snake_case` functions, `PascalCase` classes,
  `UPPER_SNAKE_CASE` constants.
- **Function size:** keep functions under **50 lines**; one responsibility per
  module (Single Responsibility Principle).
- **No global variables.** Pass dependencies via constructors/parameters
  (Dependency Inversion) — never module-level mutable state.
- **No business logic in CLI.** `modeldock/cli/` is a thin delivery layer that
  translates argv → `core` service calls only.
- **Communicate through interfaces.** Code against `ports/` protocols, never
  concrete adapters.

---

## Exceptions

- **NEVER raise generic `Exception`.** Always use typed exceptions.
- **All exceptions subclass `ModelDockError`** (in `common/errors.py`), e.g.
  `RuntimeUnavailableError`, `ModelNotFoundError`, `DownloadError`,
  `CacheError`, `ConfigError`, `AliasResolutionError`.
- **Always include context** in error messages — state what failed and the
  actionable next step (e.g. "Model 'llama3' not installed. Run
  `modeldock install llama3` or set `auto_install=True`.").
- **No silent swallowing.** Expected failure paths raise typed errors the
  API/CLI can catch and present; never `except: pass`.

---

## Git Workflow

- **NEVER develop on `main`.** Always branch and open a PR for review.
- **Branch naming:**
  - `feature/{desc}` — new functionality
  - `fix/{desc}` — bug fixes
  - `docs/{desc}` — documentation
  - `refactor/{desc}` — refactoring
  - `test/{desc}` — test additions/changes
  - `chore/{desc}` — maintenance, deps, tooling
- **Flow:** branch → commit → push → open PR → **user reviews** (never merge
  your own PR without explicit request).
- Commit messages: imperative, repo-style; never commit secrets or `.env`.

---

## Critical Rules (non-negotiable)

1. **NEVER place business logic in CLI commands.** CLI only calls `core`.
2. **NEVER raise generic `Exception`.** Use typed `ModelDockError` subclasses.
3. **NEVER skip the approval gate** before implementation.
4. **NEVER assume features not in `PROJECT.MD`.** Build only what is specified.
5. **ALWAYS communicate through interfaces** (`ports/`), not concrete adapters.
6. **NEVER develop on `main`** — always create a PR for review.

---

## Architecture Map (quick reference)

```
Interface:   modeldock/__init__.py (SDK)  +  modeldock/cli (Typer)
Application: modeldock/core/   (services, LifecycleOrchestrator, ModelManager)
Domain:      modeldock/domain/ (pure entities, no I/O)
Ports:       modeldock/ports/  (typing.Protocol interfaces)
Adapters:    modeldock/adapters/ (runtimes, registry, downloaders, cache, progress)
Common:      modeldock/common/ (config, logging, platform, http, errors)
Data:        modeldock/data/catalog.json (bundled model registry)
```

See `Architecture.md` §2 for the full tree and §3 for per-module responsibilities.

---

## Port Interfaces (the contract)

When implementing or extending, honor these protocols exactly:

- `RuntimePort` — `is_available`, `list_installed`, `is_installed`, `pull`,
  `remove`, `get_model_client`, `default_tag_for`.
- `RegistryPort` — `search`, `get`, `by_category`, `recommend`, `list_all`.
- `DownloaderPort` — `download`, `pull` (with `ProgressPort` reporting).
- `CachePort` — track installed/downloaded artifacts; `is_fresh`, `clean`.
- `ProgressPort` — render download/install progress (rich / tqdm / silent).
- `EventPort` — lifecycle hooks (`before_pull`, `after_install`, `on_error`).

Every adapter MUST pass the shared **port-contract test suite** (parameterized
over all implementations). This is how we guarantee new runtimes behave.

---

## Suggested Dependencies

`typer`, `httpx`, `pydantic` (v2), `platformdirs`, `rich`, `tqdm`,
`tomli`/`tomllib`, `packaging`. Dev: `pytest`, `pytest-cov`, `pytest-mock`,
`ruff`, `mypy`, `bandit`, `pre-commit`. Do not introduce others without reason.

---

## Workflow for Agents

1. **Discover** — Read `PROJECT.MD`, `Architecture.md`, and any context files.
   Use ContextScout for project standards before coding.
2. **Propose** — Summarize what/where/approach. Request approval. No files yet.
3. **Init session** — On approval, create `.tmp/sessions/<date>-<slug>/` and a
   `context.md` capturing requirements + standards.
4. **Plan** — Break into atomic subtasks (TaskManager for complex work). Mark
   independent tasks `parallel: true`.
5. **Execute** — One step at a time; validate (type-check, lint, test) after
   each. Parallelize independent batches.
6. **Validate & handoff** — Run full test suite; suggest TestEngineer /
   CodeReviewer; summarize; ask user to clean up `.tmp`.

---

## Testing Expectations

- Unit: domain + pure functions, no network/runtime. Target ≥80% coverage.
- Port-contract: shared suite over every adapter implementation.
- Integration: real/containerized Ollama, skipped if absent
  (`@pytest.mark.integration`).
- E2E: CLI via `CliRunner`/`subprocess`.
- Use fake `RuntimePort`/`RegistryPort`/`CachePort` fixtures so core logic is
  testable without Ollama installed.
- CI matrix: Windows / macOS / Linux × Python 3.9–3.12.

---

## Conventions

- Type hints on all public functions; `mypy --strict` clean.
- `ruff` for lint + format (line length 100).
- Pydantic v2 for data models; `snake_case`/`PascalCase`/`UPPER_SNAKE_CASE`.
- Functions < 50 lines; one responsibility per module; no global variables.
- Public API lives only in `modeldock/__init__.py`; keep it narrow and stable.
- Docstrings: concise, document *why* not *what*; avoid noise.
- No emojis in code/docs unless explicitly requested.

---

## Extension Checklist (adding a new runtime)

- [ ] Create `modeldock/adapters/runtimes/<name>.py` implementing `RuntimePort`.
- [ ] Subclass `BaseRuntime` for shared logic (alias resolution, availability
      caching, error normalization).
- [ ] Add entry point in `pyproject.toml`:
      `[project.entry-points."modeldock.runtimes"] <name> = "..."`.
- [ ] Add/extend port-contract tests; ensure they pass.
- [ ] Document backend-specific notes (install, host, capabilities).
- [ ] Do NOT touch `core/`, `cli/`, or the public API.

---

*When in doubt, re-read `Architecture.md`. When conflicting with this file,
`Architecture.md` is authoritative for design; `PROJECT.MD` is authoritative for
product intent. The **Critical Rules** and **Coding Standards** sections above
are non-negotiable for any code written in this repo.*
