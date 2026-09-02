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

For runtimes that download raw files (llama.cpp GGUF, GPT4All), weights are kept in a content-addressed store (`cache/blobs/<sha256[:2]>/<sha256>`), which makes re-installs instant offline.

The readable path you hand to `llama-server` — `cache/models/<name>/<tag>.gguf` — is a hard link onto that blob, so two models whose weights are byte-identical share one copy on disk instead of costing you the download twice. (On filesystems without hard links, ModelDock falls back to a copy.)

### Smart Caching Logic

- `CacheService.is_fresh(ref)` compares requested tag/spec against manifest + runtime state
- Content hashing (SHA-256) makes the cache path-independent and self-validating
- When the catalog publishes a model's SHA-256 and those exact bytes are already stored, installing skips the download entirely and just links
- `cache.clean()` removes partial downloads and orphaned artifacts, including weights no cached model refers to any more
- Removing one model never deletes weights another cached model is still using

---

## Offline Mode

If `auto_install` is off or network is unavailable, `load()` fails fast with a clear "model not installed and offline" message rather than hanging.

---

## Next Steps

- [Configuration](configuration.md) — change cache location
- [Architecture: Cache](../architecture/overview.md) — design details
