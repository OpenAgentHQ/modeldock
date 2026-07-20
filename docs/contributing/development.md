# Development Setup

Full development environment setup.

---

## Prerequisites

- Python 3.9–3.12
- Git
- A local [Ollama](https://ollama.com) install (for integration tests)

---

## Environment Setup

```bash
# Clone
git clone https://github.com/OpenAgentHQ/modeldock.git
cd modeldock

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install in editable mode with dev + ollama extras
pip install -e ".[dev,ollama]"
pre-commit install
```

---

## Project Layout

```
src/modeldock/        # package source (src/ layout)
tests/                # unit / integration / e2e
.opencode/            # agent + tooling config (not shipped)
PROJECT.MD            # product intent
Architecture.md       # design contract
AGENT.md              # agent/contributor rules
pyproject.toml        # build, deps, tooling, entry points
```

---

## Build & Package

```bash
# Build sdist + wheel
python -m build

# Or install editable
pip install -e .
```

---

## Code Quality

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

---

## Testing

```bash
# Everything (unit + contract + e2e)
pytest

# Unit only (fast, no network/runtime)
pytest tests/unit

# Port-contract suite
pytest tests/unit -k contract

# Integration (requires Ollama)
pytest tests/integration -m integration

# E2E (CLI)
pytest tests/e2e

# Coverage (target ≥80%)
pytest --cov=modeldock --cov-report=term-missing
```

### Test Layers

| Layer | Needs | Markers |
|-------|-------|---------|
| Unit | nothing | (default) |
| Port-contract | fake ports | `-k contract` |
| Integration | real Ollama | `-m integration` |
| E2E | CLI entry point | `-m e2e` |

---

## Local CLI

```bash
# As installed console script
modeldock --help
modeldock list

# Or via module
python -m modeldock --help
```

---

## Debugging Tips

- Enable DEBUG logging: `modeldock --log-level DEBUG ...`
- Inspect cache: `modeldock cache status` / `modeldock cache path`
- Verify runtime: `python -c "import modeldock; print(md.installed())"`
- Use fake adapters in tests to isolate core logic

---

## CI (GitHub Actions)

Matrix: Windows / macOS / Linux × Python 3.9–3.12.

Steps per job:

1. Setup Python
2. `pip install -e ".[dev,ollama]"`
3. `ruff check` + `ruff format --check`
4. `mypy src`
5. `bandit -r src`
6. `pytest`
7. Upload coverage

---

## Next Steps

- [Adding Runtimes](new-runtime.md) — extension workflow
- [Testing Strategy](testing.md) — test layers
