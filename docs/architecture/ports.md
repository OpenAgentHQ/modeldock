# Port Interfaces

The contract that every adapter must honor.

---

## Why Ports?

Ports define *what* the system needs from the outside world. Adapters provide *how*. This is Dependency Inversion — the core depends on abstractions, not concrete implementations.

---

## RuntimePort

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

## RegistryPort

```python
class RegistryPort(Protocol):
    def search(self, query: str) -> list: ...
    def get(self, ref: ModelRef) -> ModelSpec | None: ...
    def by_category(self, cat: Category) -> list: ...
    def recommend(self, task: str) -> list: ...
    def list_all(self) -> list: ...
```

---

## DownloaderPort

```python
class DownloaderPort(Protocol):
    def download(self, spec: ModelSpec, dest: Path, progress: ProgressPort) -> Path: ...
    def pull(self, ref: ModelRef, progress: ProgressPort) -> PullResult: ...
```

---

## CachePort

```python
class CachePort(Protocol):
    def is_fresh(self, ref: ModelRef) -> bool: ...
    def clean(self, force: bool = False) -> list[str]: ...
    def path(self) -> str: ...
    def status(self) -> list[dict]: ...
```

---

## ProgressPort

```python
class ProgressPort(Protocol):
    def start(self, description: str, total: int | None = None) -> None: ...
    def update(self, increment: int) -> None: ...
    def finish(self) -> None: ...
```

---

## EventPort

```python
class EventPort(Protocol):
    def before_pull(self, ref: ModelRef) -> None: ...
    def after_install(self, ref: ModelRef) -> None: ...
    def on_error(self, ref: ModelRef, error: Exception) -> None: ...
```

---

## Port-Contract Test Suite

Every adapter MUST pass the shared port-contract test suite — parameterized over all implementations. This guarantees new runtimes behave correctly.

```bash
pytest tests/unit -k contract
```

---

## Next Steps

- [Runtime Adapters](runtime-adapters.md) — implementing ports
- [Error Handling](errors.md) — typed exceptions
