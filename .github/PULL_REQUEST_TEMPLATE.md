## Summary

<!-- What does this PR do and why? Keep it concise. -->

## Changes

<!-- Bullet the meaningful changes. Wrap file paths in backticks, e.g. `src/modeldock/core/lifecycle.py`. -->

-

## Testing

<!-- How was this verified? Commands, layers (unit/integration/e2e), coverage. -->

-

## Checklist

- [ ] Branch named per Git Workflow (`feature/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`)
- [ ] Not developed on `main`
- [ ] Code follows `AGENT.md` coding standards (type hints, Pydantic v2, no generic `Exception`, no business logic in CLI)
- [ ] `domain/` and `ports/` stay pure (no I/O, no framework imports)
- [ ] Quality gates pass locally: `ruff`, `mypy --strict`, `bandit`, `pytest`
- [ ] Docs updated if behavior changed
- [ ] `pyproject.toml` and `src/modeldock/__init__.py` versions match (if release-related)
