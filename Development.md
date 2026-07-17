# Development — ModelDock

Guide for contributors and AI coding agents setting up, building, testing, and
extending ModelDock. For product intent read [`PROJECT.MD`](./PROJECT.MD); for
the design contract read [`Architecture.md`](./Architecture.md); for agent
rules read [`AGENT.md`](./AGENT.md).

---

## 1. Prerequisites

- Python 3.9–3.12 (tested on the CI matrix: 3.9, 3.10, 3.11, 3.12)
- A local [Ollama](https://ollama.com) install for integration tests
  (unit/contract tests need none)
- `git`, and a virtual environment tool of choice (`venv`, `conda`, `uv`)

---

## 2. Environment Setup

```bash
# Clone
git clone https://github.com/OpenAgentHQ/modeldock.git
cd modeldock

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install in editable mode with dev + ollama extras
pip install -e ".[dev,ollama]"
```

`pyproject.toml` declares these extras:

- `ollama` — optional runtime-native SDK (`ollama` Python client)
- `dev` — `pytest`, `pytest-cov`, `pytest-mock`, `ruff`, `mypy`, `bandit`,
  `pre-commit`

---

## 3. Project Layout (dev view)

```
src/modeldock/        # package source (src/ layout)
tests/                # unit / integration / e2e
.opencode/            # agent + tooling config (not shipped)
PROJECT.MD            # product intent
Architecture.md       # design contract
AGENT.md              # agent/contributor rules
QUICKSTART.md         # user quickstart
Development.md        # this file
pyproject.toml        # build, deps, tooling, entry points
```

---

## 4. Build & Packaging

ModelDock uses a standard `pyproject.toml` (PEP 621) with a `src/` layout. No
build backend magic required beyond `pip`/`build`.

```bash
# Build sdist + wheel
python -m build

# Or install editable (see §2)
pip install -e .
```

Entry point (console script):

```toml
[project.scripts]
modeldock = "modeldock.cli.app:main"
```

Runtime plugins are discovered via:

```toml
[project.entry-points."modeldock.runtimes"]
ollama = "modeldock.adapters.runtimes.ollama:OllamaRuntime"
```

---

## 5. Code Quality (run locally before committing)

```bash
# Lint + format (ruff)
ruff check src tests
ruff format src tests

# Type checking (strict)
mypy src

# Security scan
bandit -r src -c pyproject.toml

# All-in-one via pre-commit
pre-commit run --all-files
```

Pre-commit is configured to run ruff, mypy, and bandit on every commit.

---

## 6. Testing

```bash
# Everything (unit + contract + e2e); integration skipped if no Ollama
pytest

# Unit only (fast, no network/runtime)
pytest tests/unit

# Port-contract suite (parameterized over all adapters)
pytest tests/unit -k contract

# Integration (requires Ollama running)
pytest tests/integration -m integration

# E2E (CLI via subprocess / CliRunner)
pytest tests/e2e

# Coverage (target ≥80%)
pytest --cov=modeldock --cov-report=term-missing
```

**Test layers:**

| Layer | Needs | Markers |
|---|---|---|
| Unit | nothing | (default) |
| Port-contract | fake ports (fixtures) | `-k contract` |
| Integration | real/containerized Ollama | `-m integration` |
| E2E | CLI entry point | `-m e2e` |

Integration tests auto-skip when Ollama is unavailable, so CI stays green
without a runtime. Use fake `RuntimePort`/`RegistryPort`/`CachePort` fixtures
(`tests/conftest.py`) so core logic is testable without any runtime installed.

---

## 7. Local CLI & REPL

```bash
# As installed console script
modeldock --help
modeldock list
modeldock install llama3

# Or via module (no install needed in editable mode)
python -m modeldock --help
```

---

## 8. Configuration During Development

Config precedence (low → high): built-in defaults → bundled `catalog.json` →
system config → user config (`~/.config/modeldock/config.toml` or
`%APPDATA%\modeldock\config.toml`) → env vars (`MODELDOCK_*`) → runtime overrides.

```bash
modeldock config show
modeldock config set log_level DEBUG
```

Useful env vars:

- `MODELDOCK_LOG_LEVEL` — `DEBUG`/`INFO`/`WARNING`/`ERROR`
- `MODELDOCK_DEFAULT_BACKEND` — `ollama`
- `MODELDOCK_AUTO_INSTALL` — `true`/`false`
- `MODELDOCK_CACHE_DIR` — override cache location

---

## 9. Adding a New Runtime (extension workflow)

Follow the Open/Closed rule — **no core edits**.

1. Create `src/modeldock/adapters/runtimes/<name>.py`.
2. Implement `RuntimePort` (see `Architecture.md` §4). Subclass `BaseRuntime`
   for shared logic (alias resolution, availability caching, error
   normalization).
3. Add an entry point in `pyproject.toml`:
   ```toml
   [project.entry-points."modeldock.runtimes"]
   <name> = "modeldock.adapters.runtimes.<name>:<Name>Runtime"
   ```
4. Add/extend the **port-contract tests**; ensure they pass.
5. Document backend-specific install/host/capability notes.
6. Do **not** modify `core/`, `cli/`, or the public API in
   `modeldock/__init__.py`.

See `AGENT.md` → "Extension Checklist" for the full list.

---

## 10. Adding Models to the Registry

Edit `src/modeldock/data/catalog.json` (no code change). Each entry:

```json
{
  "name": "llama3",
  "aliases": ["llama3", "llama-3"],
  "category": "chat",
  "capabilities": ["chat", "completion"],
  "default_tag": "latest",
  "variants": [
    { "tag": "8b", "params": "8B", "size_bytes": 4660000000, "min_ram": "8GB" }
  ],
  "description": "Meta Llama 3 instruction model.",
  "backend_hints": ["ollama"]
}
```

Optional `RemoteRegistry` can refresh the catalog from a URL without a release.

---

## 11. Debugging Tips

- Enable `DEBUG` logging: `modeldock --log-level DEBUG ...` or
  `MODELDOCK_LOG_LEVEL=DEBUG`.
- Inspect cache state: `modeldock cache status` / `modeldock cache path`.
- Verify a runtime is detected: `python -c "import modeldock; print(md.installed())"`.
- For download issues, check checksum mismatch errors — they raise
  `DownloadError` with a retry suggestion; never install corrupt weights.
- Use fake adapters in tests to isolate core logic from network/runtime.

---

## 12. CI (GitHub Actions)

Matrix: Windows / macOS / Linux × Python 3.9–3.12.

Steps per job:

1. Setup Python (matrix version)
2. `pip install -e ".[dev,ollama]"`
3. `ruff check` + `ruff format --check`
4. `mypy src`
5. `bandit -r src`
6. `pytest` (integration auto-skips without Ollama)
7. Upload coverage

---

## 13. Release Checklist

- [ ] Bump version in `pyproject.toml`
- [ ] `ruff` + `mypy` + `bandit` clean
- [ ] `pytest` green (all layers)
- [ ] Docs current: `PROJECT.MD`, `Architecture.md`, `AGENT.md`, `QUICKSTART.md`
- [ ] `python -m build` produces sdist + wheel
- [ ] Tag release, publish to PyPI (`twine upload dist/*`)
- [ ] Verify `pip install modeldock` in a clean venv

---

*Keep this file in sync with `Architecture.md` and `AGENT.md`. When conflicts
arise, `Architecture.md` is authoritative for design.*
