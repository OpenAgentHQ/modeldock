# Discover Models

Browse, search, and recommend models from the dynamic catalog.

---

## Browse the Catalog

```python
import modeldock as md

# List all known models
models = md.list()
```

---

## Search by Name, Capability, or Category

```python
# Search by keyword
results = md.search("coding")

# Search by capability
results = md.search("vision")

# Search by category
results = md.search("embedding")
```

---

## Get Model Info

```python
info = md.info("qwen3")
# Returns: sizes, capabilities, variants, installed tags
```

---

## Get Recommendations

```python
# Guided pick for a specific task
models = md.recommend(task="coding")
models = md.recommend(task="vision")
```

---

## List Categories

```python
categories = md.categories()
```

---

## What's Installed Locally

```python
installed = md.installed()
# Returns list of ModelRef objects for models present in your runtime
```

---

## Dynamic Catalog

ModelDock scrapes `ollama.com/library` for a live model catalog, cached locally for 24 hours. New models appear automatically after catalog refresh.

### Catalog Source

Control which registry is used:

| Value | Behavior |
|-------|----------|
| `auto` | Try dynamic, fallback to bundled (default) |
| `ollama` | Dynamic only — requires internet |
| `bundled` | Static catalog.json only — fully offline |

Set via config or `MODELDOCK_CATALOG_SOURCE` env var.

---

## Next Steps

- [Install & Manage](install.md) — download and manage models
- [Configuration](configuration.md) — change catalog source
