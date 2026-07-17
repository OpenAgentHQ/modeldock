# Contributing to ModelDock

Thank you for your interest in contributing! This document provides guidelines
and instructions for contributing to ModelDock.

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating,
you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A local [Ollama](https://ollama.com) install (for integration tests)

### Finding Something to Work On

- **Good First Issues**: Look for issues labeled `good first issue`
- **Help Wanted**: Check issues labeled `help wanted`
- **Documentation**: Help improve the docs in this repo
- **Tests**: Add or improve test coverage (target ≥80%)

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/modeldock.git
cd modeldock
```

### 2. Add Upstream Remote

```bash
git remote add upstream https://github.com/OpenAgentHQ/modeldock.git
```

### 3. Create and Activate a Virtual Environment

**Always work inside a virtual environment — never install into global Python.**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -e ".[dev,ollama]"
pre-commit install
```

### 5. Create a Branch

```bash
git fetch upstream
git checkout -b feature/my-change upstream/main
```

### 6. Verify Setup

```bash
pytest
ruff check src tests
mypy src
```

## Making Changes

### Branch Naming

| Type | Format | Example |
|------|--------|---------|
| Feature | `feature/{description}` | `feature/ollama-progress` |
| Bug Fix | `fix/{description}` | `fix/cache-manifest` |
| Documentation | `docs/{description}` | `docs/update-readme` |
| Refactor | `refactor/{description}` | `refactor/extract-runtime-base` |
| Test | `test/{description}` | `test/add-contract-suite` |
| Chore | `chore/{description}` | `chore/bump-deps` |

### Coding Standards

ModelDock enforces strict standards (see [AGENT.md](AGENT.md)):

- Python 3.10+, type hints on **all** public functions; `mypy --strict` clean.
- Pydantic v2 for all data models.
- `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- Functions under 50 lines; one responsibility per module.
- No global variables; pass dependencies via constructors (Dependency Inversion).
- **No business logic in CLI** — `modeldock/cli/` only calls `core`.
- **Never raise generic `Exception`** — use `ModelDockError` subclasses with context.
- Keep `domain/` and `ports/` pure (no I/O, no framework imports).
- Communicate through `ports/` interfaces, not concrete adapters.

### Testing

- Write tests for new features; maintain or improve coverage (≥80%).
- Layers: unit (`tests/unit`), port-contract (`pytest -k contract`),
  integration (`pytest -m integration`, auto-skips without Ollama), e2e
  (`pytest -m e2e`).
- Mock all external dependencies; test success **and** failure paths.
- Use fake `RuntimePort`/`RegistryPort`/`CachePort` fixtures.

```bash
pytest --cov=modeldock --cov-report=term-missing
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <description>
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(registry): add remote catalog refresh` |
| `fix` | Bug fix | `fix(cache): handle partial download cleanup` |
| `docs` | Documentation | `docs(readme): add configuration table` |
| `style` | Formatting | `style: fix ruff import order` |
| `refactor` | Code refactoring | `refactor(runtime): extract BaseRuntime` |
| `test` | Tests | `test(downloader): add resume tests` |
| `chore` | Maintenance | `chore: bump pydantic to 2.5` |
| `ci` | CI/CD | `ci: add release workflow` |

### Rules

- Use imperative mood ("add feature" not "added feature").
- Keep subject line under 72 characters.
- Reference issues when applicable (`fix(cache): ... (#42)`).
- No period at the end of the subject line.

## Pull Request Process

### Before Submitting

1. Update your branch:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. Run all checks:
   ```bash
   ruff check src tests && ruff format src tests
   mypy src
   bandit -r src
   pytest
   ```
3. Fill out the PR template completely.
4. Update documentation if behavior changed.

### Submitting

1. Push your branch.
2. Create a pull request against `main`.
3. Add appropriate labels.
4. Request review from maintainers.

### Review Process

1. Maintainers review your PR.
2. Address feedback promptly on the same branch.
3. Once approved, a maintainer merges (do not self-merge).

## Reporting Issues

### Bug Reports

Use the Bug Report template and include: clear description, steps to reproduce,
expected vs actual behavior, environment details.

### Feature Requests

Use the Feature Request template and include: clear description, use case,
alternatives considered.

### Security Issues

For security issues, see [SECURITY.md](SECURITY.md). **Do not** create public
issues for security vulnerabilities.

## License

By contributing, you agree that your contributions will be licensed under the
Apache 2.0 License — see [LICENSE](LICENSE).

## Questions?

Open a discussion or create an issue with the `question` label. Thank you for
contributing to ModelDock!
