# Contributing Guidelines

Thank you for your interest in contributing to ModelDock!

---

## Getting Started

1. **Fork and clone** the repo
2. **Create a virtual environment** — never install globally
3. **Install dependencies** with dev extras
4. **Create a branch** from `main`

```bash
git clone https://github.com/your-username/modeldock.git
cd modeldock
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,ollama]"
pre-commit install
git checkout -b feature/my-change
```

---

## Workflow

```
branch → discover → propose → approve → init session → plan → execute → validate → PR
```

1. **Branch first** — never work on `main`
2. **Discover** — read relevant files (QUICKSTART.md, AGENT.md, Architecture.md)
3. **Plan** — create concrete execution plan
4. **Propose & approve** — get user sign-off before coding
5. **Execute** — one step at a time, validate after each
6. **Validate** — run full test suite
7. **PR** — commit, push, open PR for review

---

## Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/{desc}` | `feature/ollama-progress` |
| Bug Fix | `fix/{desc}` | `fix/cache-manifest` |
| Documentation | `docs/{desc}` | `docs/update-readme` |
| Refactor | `refactor/{desc}` | `refactor/extract-runtime-base` |
| Test | `test/{desc}` | `test/add-contract-suite` |
| Chore | `chore/{desc}` | `chore/bump-deps` |

---

## Coding Standards

- Python 3.10+, type hints on **all** public functions; `mypy --strict` clean
- Pydantic v2 for all data models
- `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Functions under 50 lines; one responsibility per module
- No global variables; pass dependencies via constructors (Dependency Inversion)
- **No business logic in CLI** — CLI only calls `core`
- **Never raise generic `Exception`** — use `ModelDockError` subclasses with context
- Keep `domain/` and `ports/` pure (no I/O, no framework imports)
- Communicate through `ports/` interfaces, not concrete adapters

---

## Commit Guidelines

### Format

```
<type>(<scope>): <description>
```

### Types

| Type | Example |
|------|---------|
| `feat` | `feat(registry): add remote catalog refresh` |
| `fix` | `fix(cache): handle partial download cleanup` |
| `docs` | `docs(readme): add configuration table` |
| `refactor` | `refactor(runtime): extract BaseRuntime` |
| `test` | `test(downloader): add resume tests` |
| `chore` | `chore: bump pydantic to 2.5` |

### Rules

- Imperative mood ("add" not "added")
- Subject under 72 characters
- Reference issues when applicable

---

## Pull Request Process

### Before Submitting

1. Rebase on upstream `main`
2. Run all quality gates:
   ```bash
   ruff check src tests && ruff format src tests
   mypy src
   bandit -r src
   pytest
   ```
3. Update docs if behavior changed

### Review Process

1. Maintainers review your PR
2. Address feedback on the same branch
3. Once approved, a maintainer merges (never self-merge)

---

## Quality Gates

```bash
ruff check src tests          # lint
ruff format src tests         # format
mypy src                      # type check
bandit -r src                 # security
pytest --cov=modeldock        # tests + coverage
pre-commit run --all-files    # all-in-one
```

Targets: ruff clean, `mypy --strict` clean, bandit clean, ≥80% coverage.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
