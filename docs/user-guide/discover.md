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
# Returns: sizes, capabilities, variants, installed tags, and source provenance
print(info.source)   # e.g. "Ollama Official"
```

---

## Provenance — Where a Model Came From

Every discovered model carries a `source` label so you always know which
source of truth it came from, without having to know which source holds it:

```python
for spec in md.search("qwen"):
    print(spec.name, "→", spec.source)   # e.g. "Ollama Official", "Hugging Face"
```

Resolve a friendly name to its canonical spec, or list its known versions:

```python
spec = md.resolve("llama3")      # friendly name → canonical identity (+ source)
tags = md.versions("qwen3")      # e.g. ["latest", "8b", "4b"]
```

---

## Inspect the Active Sources

See which sources are feeding discovery and whether each is populated:

```python
for info in md.sources():
    print(info.name, info.trust.value, info.model_count, info.available)
```

From the CLI:

```bash
modeldock sources           # list active sources + trust/kind/backend/count/status
modeldock sources refresh   # force live sources to re-fetch (bypass cache TTL)
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

## Dynamic Discovery Is the Source of Truth

There is **no hand-maintained catalog**. ModelDock discovers models live from
each source of truth — `ollama.com/library` for Ollama, the Hugging Face Hub
API for GGUF runtimes (LM Studio, llama.cpp) — cached locally for 24 hours.
New models appear automatically; adding a model a supported source already
exposes requires **zero code changes** (no `catalog.json` edit, no manual
registration).

Three caches are kept strictly separate:

- **Discovery cache** — provider/model metadata (`sources refresh` reloads it).
- **Installed state** — what your runtime actually has (`md.installed()`).
- **Artifact cache** — downloaded files/blobs (`md.cache.*`).

### Catalog Source

Control which sources are used:

| Value | Behavior |
|-------|----------|
| `auto` | Live sources (Ollama + the active backend's own), fallback to bundled (default) |
| `ollama` | Live Ollama only — requires internet |
| `bundled` | Static `catalog.json` only — fully offline |

`bundled` is an **emergency/offline fallback only** — a tiny bootstrap set,
never the primary source. Set via config or the `MODELDOCK_CATALOG_SOURCE`
env var.

---

## Scripting — JSON Output

Every read-only discovery command has a `--json` flag for automation. It prints
one JSON document on stdout and nothing else, so it pipes cleanly:

```bash
# Names of every catalog model
modeldock list --json | jq -r '.[].name'

# Every vision model's default tag
modeldock search vision --json | jq -r '.[] | "\(.name):\(.default_tag)"'

# Is a model installed?
modeldock info llama3 --json | jq '.installed'

# Which runtimes are reachable right now?
modeldock runtimes --json | jq -r '.[] | select(.available) | .backend'
```

`info` returns a single object; `list`, `search`, `installed`, and `runtimes`
return arrays. Errors go to stderr as `{"error": {"type": ..., "message": ...}}`
with exit code 1, so stdout stays valid JSON either way.

See the [CLI Reference](../sdk/cli.md#json-output) for the full contract.

---

## Next Steps

- [Install & Manage](install.md) — download and manage models
- [Configuration](configuration.md) — change catalog source
