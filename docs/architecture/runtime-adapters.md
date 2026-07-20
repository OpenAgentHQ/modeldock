# Runtime Adapters

The heart of ModelDock's extensibility.

---

## How Runtimes Work

Each runtime implements `RuntimePort` — a protocol that defines the contract:

```python
class RuntimePort(Protocol):
    backend: RuntimeBackend

    def is_available(self) -> bool: ...
    def list_installed(self) -> list[ModelRef]: ...
    def is_installed(self, ref: ModelRef) -> bool: ...
    def pull(self, ref: ModelRef, progress: ProgressPort) -> PullResult: ...
    def remove(self, ref: ModelRef) -> None: ...
    def get_model_client(self, ref: ModelRef) -> ModelClient: ...
    def default_tag_for(self, spec: ModelSpec) -> str: ...
```

---

## BaseRuntime

`adapters/runtimes/base.py` provides shared logic so each concrete runtime only implements runtime-specific calls:

- Alias resolution
- Availability caching
- Error normalization

---

## Ollama (Shipped)

The first runtime, fully implemented in `adapters/runtimes/ollama.py`.

---

## Adding a New Runtime

### 1. Create the Adapter

```python
# src/modeldock/adapters/runtimes/lmstudio.py
from modeldock.ports.runtime import RuntimePort

class LMStudioRuntime(BaseRuntime):
    backend = RuntimeBackend.LMSTUDIO

    def is_available(self) -> bool:
        # Check if LM Studio is installed/running
        ...

    def list_installed(self) -> list[ModelRef]:
        # Query LM Studio for installed models
        ...

    # ... implement all RuntimePort methods
```

### 2. Register via Entry Point

In `pyproject.toml`:

```toml
[project.entry-points."modeldock.runtimes"]
lmstudio = "modeldock.adapters.runtimes.lmstudio:LMStudioRuntime"
```

### 3. Add Port-Contract Tests

Extend the shared test suite parameterized over all adapters.

### 4. Document Backend-Specific Notes

Install, host, capability notes for the new runtime.

### 5. Do NOT Touch Core/CLI/API

The extension is self-contained. No changes to `core/`, `cli/`, or `modeldock/__init__.py`.

---

## Runtime Selection

`ModelManager` picks a runtime via:

1. Explicit `backend=` argument
2. Config default (`default_backend`)
3. Auto-detection of which runtimes are installed

This is Open/Closed: new runtimes register themselves without touching the manager.

---

## Runtime Registry

A `RuntimeRegistry` maps `RuntimeBackend` → factory. Discovered via entry points or an internal registry dict.

---

## Next Steps

- [Port Interfaces](ports.md) — the full contract
- [Adding Runtimes](../contributing/new-runtime.md) — contributor guide
