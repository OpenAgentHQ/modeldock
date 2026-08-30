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

Extend the shared test suite in `tests/unit/test_port_contract.py` parameterized over all adapters.

Every runtime adapter must have a factory function in `tests/unit/test_port_contract.py` wired with fake ports/clients (so no external daemon or network is required) and be registered in `_ALL_RUNTIME_FACTORIES` (as well as `_LIFECYCLE_RUNTIME_FACTORIES` or `_PLAN_ONLY_RUNTIME_FACTORIES` as appropriate):

```python
# tests/unit/test_port_contract.py
def _make_faked_myruntime() -> RuntimePort:
    from modeldock.adapters.runtimes.myruntime import MyRuntime

    runtime = MyRuntime()
    runtime._client = _FakeMyClient()
    runtime._availability = True
    return runtime


_ALL_RUNTIME_FACTORIES.append(_make_faked_myruntime)
```

Ensure the port-contract test suite passes:

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

## Step 6 (optional): Add a Live Catalog Provider

If the runtime has its own online model catalog (or one it borrows, like LM
Studio and llama.cpp both borrowing the Hugging Face Hub), you can wire it
into `md.search()`/`md.list()`/`md.recommend()` the same way — one more
entry-point line, no core edits:

```toml
[project.entry-points."modeldock.catalog_providers"]
lmstudio = "modeldock_lmstudio.catalog:build_catalog"
```

The entry point resolves to a callable `(cache_dir: Path) -> RegistryPort` —
a plain function, or a class whose constructor takes only `cache_dir`:

```python
# modeldock_lmstudio/catalog.py
from pathlib import Path
from modeldock.ports.registry import RegistryPort

def build_catalog(cache_dir: Path) -> RegistryPort:
    """Return a RegistryPort backed by this runtime's own catalog."""
    return MyLiveCatalog(cache_dir)
```

`ModelManager._resolve_backend_catalog` resolves it through
`CatalogProviderRegistry` (`adapters/registry/catalog_registry.py`) and
merges it with the general catalog via `CompositeRegistry`, so results
surface alongside the shared Ollama-named catalog rather than replacing it.
Without a catalog provider, the runtime's `models_for_category`/
`models_for_capability` (Step 1) still work for `install_category()` — this
step only affects general discovery. See Architecture.md §9/§14 and
`adapters/registry/huggingface_catalog.py` for a real example.

---

## Extension Checklist

- [ ] Create `modeldock/adapters/runtimes/<name>.py` implementing `RuntimePort`
- [ ] Subclass `BaseRuntime` for shared logic
- [ ] Add entry point in `pyproject.toml`
- [ ] Add/extend port-contract tests
- [ ] Document backend-specific notes
- [ ] (Optional) Add a `modeldock.catalog_providers` entry point for live discovery
- [ ] Do NOT touch `core/`, `cli/`, or public API

---

## Next Steps

- [Runtime Adapters](../architecture/runtime-adapters.md) — design details
- [Port Interfaces](../architecture/ports.md) — the contract
