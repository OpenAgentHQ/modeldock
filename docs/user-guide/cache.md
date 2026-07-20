# Cache Management

ModelDock tracks what's installed and cached so you never re-download.

---

## Check Cache Status

```python
import modeldock as md

entries = md.cache.status()
```

---

## Get Cache Path

```python
path = md.cache.path()
```

---

## Clean the Cache

Safe by default — only removes corrupt/partial entries:

```python
md.cache.clean()
```

Force wipe everything:

```python
md.cache.clean(force=True)
```

---

## How Caching Works

ModelDock maintains two cache concepts:

### Installed-Model Cache

Tracks models already pulled into the runtime (Ollama's store). Verified via `runtime.list_installed()` plus a local manifest.

### Download Artifact Cache

For runtimes that download raw files (llama.cpp GGUF, GPT4All), a content-addressed store (`cache/<sha256[:16]>/model.gguf`) makes re-installs instant offline.

### Smart Caching Logic

- `CacheService.is_fresh(ref)` compares requested tag/spec against manifest + runtime state
- Content hashing (SHA-256) makes the cache path-independent and self-validating
- `cache.clean()` removes partial downloads and orphaned artifacts

---

## Offline Mode

If `auto_install` is off or network is unavailable, `load()` fails fast with a clear "model not installed and offline" message rather than hanging.

---

## Next Steps

- [Configuration](configuration.md) — change cache location
- [Architecture: Cache](../architecture/overview.md) — design details
