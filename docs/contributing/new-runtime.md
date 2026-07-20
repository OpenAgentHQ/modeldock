# Adding New Runtimes

Step-by-step guide to adding a new runtime adapter.

---

## The Open/Closed Rule

Adding a new runtime = one new adapter class + one entry-point line. **No core edits.**

---

## Step 1: Create the Adapter

```python
# src/modeldock/adapters/runtimes/lmstudio.py
from __future__ import annotations

from modeldock.adapters.runtimes.base import BaseRuntime
from modeldock.domain.model import ModelRef, RuntimeBackend
from modeldock.ports.progress import ProgressPort

class LMStudioRuntime(BaseRuntime):
    backend = RuntimeBackend.LMSTUDIO

    def is_available(self) -> bool:
        """Check if LM Studio is installed and running."""
        ...

    def list_installed(self) -> list[ModelRef]:
        """Query LM Studio for installed models."""
        ...

    def is_installed(self, ref: ModelRef) -> bool:
        """Check if a specific model is installed."""
        ...

    def pull(self, ref: ModelRef, progress: ProgressPort) -> PullResult:
        """Download/install a model."""
        ...

    def remove(self, ref: ModelRef) -> None:
        """Uninstall a model."""
        ...

    def get_model_client(self, ref: ModelRef) -> ModelClient:
        """Return a ready-to-use client."""
        ...

    def default_tag_for(self, spec: ModelSpec) -> str:
        """Resolve the default variant tag."""
        ...
```

---

## Step 2: Register via Entry Point

In `pyproject.toml`:

```toml
[project.entry-points."modeldock.runtimes"]
lmstudio = "modeldock.adapters.runtimes.lmstudio:LMStudioRuntime"
```

---

## Step 3: Add Port-Contract Tests

Extend the shared test suite parameterized over all adapters:

```python
# tests/unit/test_runtime_contract.py
@pytest.mark.parametrize("runtime", [OllamaRuntime(), LMStudioRuntime()])
def test_list_installed(runtime):
    """All runtimes must return a list from list_installed."""
    result = runtime.list_installed()
    assert isinstance(result, list)
```

Ensure they pass:

```bash
pytest tests/unit -k contract
```

---

## Step 4: Document Backend-Specific Notes

Create `docs/sdk/<runtime>.md` with:

- Installation requirements
- Host/connection details
- Capability differences
- Any limitations

---

## Step 5: Do NOT Touch Core/CLI/API

The extension is self-contained. Do not modify:

- `modeldock/core/`
- `modeldock/cli/`
- `modeldock/__init__.py`

---

## Extension Checklist

- [ ] Create `modeldock/adapters/runtimes/<name>.py` implementing `RuntimePort`
- [ ] Subclass `BaseRuntime` for shared logic
- [ ] Add entry point in `pyproject.toml`
- [ ] Add/extend port-contract tests
- [ ] Document backend-specific notes
- [ ] Do NOT touch `core/`, `cli/`, or public API

---

## Next Steps

- [Runtime Adapters](../architecture/runtime-adapters.md) — design details
- [Port Interfaces](../architecture/ports.md) — the contract
