# Testing Strategy

ModelDock tests in layers — each with different requirements and speed.

---

## Test Layers

| Layer | Location | Needs | Run | Speed |
|-------|----------|-------|-----|-------|
| Unit | `tests/unit` | nothing | `pytest tests/unit` | Fast |
| Port-contract | `tests/unit` | fake ports | `pytest -k contract` | Fast |
| Integration | `tests/integration` | real Ollama | `pytest -m integration` | Slow |
| E2E | `tests/e2e` | CLI entry point | `pytest -m e2e` | Medium |

---

## Unit Tests

Domain logic, pure functions, port contracts. Fast, no network, no runtime.

```bash
pytest tests/unit
```

Use fake `RuntimePort`/`RegistryPort`/`CachePort` fixtures (`tests/conftest.py`) so core logic is testable without Ollama installed.

---

## Port-Contract Tests

A shared test suite parameterized over every `RuntimePort`/`DownloaderPort` implementation. Guarantees each adapter honors the interface.

```bash
pytest tests/unit -k contract
```

New runtimes MUST pass this suite.

---

## Integration Tests

Against a real or containerized Ollama when available. Auto-skips if runtime is absent.

```bash
pytest tests/integration -m integration
```

Marked with `@pytest.mark.integration`.

---

## E2E Tests

CLI invocation via `CliRunner` / `subprocess`, asserting exit codes and output.

```bash
pytest tests/e2e
```

---

## Coverage

Target: **≥80%** coverage.

```bash
pytest --cov=modeldock --cov-report=term-missing
```

---

## Writing Tests

### Use Fake Fixtures

```python
# tests/conftest.py
class FakeRuntimePort:
    def is_available(self) -> bool:
        return True
    def list_installed(self) -> list[ModelRef]:
        return []
    # ...
```

### Test Success AND Failure Paths

```python
def test_load_missing_model():
    """load() should raise ModelNotInstalledError when auto_install=False."""
    ...

def test_load_existing_model():
    """load() should return client for installed model."""
    ...
```

### Mock External Dependencies

Never hit real networks or runtimes in unit tests.

---

## CI Matrix

GitHub Actions runs on:

- Windows / macOS / Linux
- Python 3.9, 3.10, 3.11, 3.12

---

## Next Steps

- [Development Setup](development.md) — full dev environment
- [Contributing Guidelines](guidelines.md) — how to contribute
