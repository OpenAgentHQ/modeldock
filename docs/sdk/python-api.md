# Python API Reference

Full reference for the ModelDock Python SDK.

---

## Import

```python
import modeldock as md
```

---

## Core Functions

### `load(name, backend=None, auto_install=None)`

Auto-install if missing, then return a ready-to-use client.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Model name (e.g., `"llama3"`) |
| `backend` | `str?` | Runtime backend (e.g., `"ollama"`) |
| `auto_install` | `bool?` | Override auto-install setting |

Returns a runtime-native client (e.g., `ollama.Client`).

---

### `install(name, backend=None)`

Explicit download of a model.

Returns `ModelRef`.

---

### `install_category(category, backend=None)`

Bulk install models by category.

Returns `list[ModelRef]`.

---

### `update(name, backend=None, confirm=False)`

Pull a newer tag. **Destructive** — removes then re-downloads. Requires `confirm=True`.

Returns `ModelRef`.

---

### `remove(name, backend=None)`

Uninstall a model.

---

### `verify(name, backend=None)`

Integrity check. Returns `bool`.

---

## Discovery Functions

### `list()`

Browse the full catalog. Returns `list`.

---

### `search(query)`

Search by name, capability, or category. Returns `list`.

---

### `installed()`

Models present locally. Returns `list[ModelRef]`.

---

### `info(name)`

Sizes, capabilities, variants. Returns model info object.

---

### `categories()`

Available categories. Returns `list[Category]`.

---

### `recommend(task)`

Guided pick for a task. Returns `list`.

---

## Execution

### `run(name, prompt=None, backend=None, **opts)`

Run a completion or interactive REPL.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Model name |
| `prompt` | `str?` | If provided, single completion; otherwise REPL |
| `backend` | `str?` | Runtime backend |
| `**opts` | | Runtime-specific options (e.g., `temperature`) |

---

## Cache

```python
md.cache.status()    # list cache entries
md.cache.path()      # real cache directory
md.cache.clean()     # safe: removes only corrupt/partial entries
md.cache.clean(force=True)  # wipes everything
```

---

## Configuration

```python
md.configure(
    backend="ollama",
    auto_install=True,
    log_level="INFO",
    progress_style="rich",
    cache_dir="/custom/path",
    ollama_host="http://localhost:11434",
)
```

---

## Explicit Manager

```python
mgr = md.Manager(
    backend="ollama",
    auto_install=True,
    ollama_host="http://localhost:11434",
)
```

---

## Exported Names

```python
__all__ = [
    "load", "list", "search", "installed", "info", "categories",
    "recommend", "install", "install_category", "update", "remove",
    "verify", "run", "cache", "configure", "Manager", "ModelManager",
    "ModelRef", "RuntimeBackend", "Category",
]
```
