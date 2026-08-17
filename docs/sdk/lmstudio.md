# LM Studio Integration

ModelDock talks to LM Studio through its local server's OpenAI-compatible API.
Most of ModelDock works identically across backends; this page documents where
LM Studio differs and why.

## Quick start

```python
import modeldock as md

mgr = md.Manager(backend="lmstudio")

mgr.installed()                       # models loaded in LM Studio
mgr.suggest_category("coding")        # what a category install would fetch
mgr.install_category("coding")        # fetch them
```

```bash
modeldock installed --backend lmstudio
modeldock install-category coding --backend lmstudio
```

## Backend-specific quirks

### Model identifiers are Hugging Face coordinates

This is the difference that shapes everything else. ModelDock's shared catalog
is built from `ollama.com/library`, so its names are Ollama tags:

```
llama3        qwen2.5-coder        nomic-embed-text
```

LM Studio addresses models by their Hugging Face coordinates instead:

```
lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF
lmstudio-community/Qwen2.5-Coder-7B-Instruct-GGUF
nomic-ai/nomic-embed-text-v1.5-GGUF
```

Handing an Ollama tag to LM Studio asks for a model it has never heard of, so
category installs cannot reuse the shared catalog's names. ModelDock keeps a
curated LM Studio mapping and routes category and capability lookups through it
automatically — you do not have to translate names yourself.

The `/` in an LM Studio identifier is part of the **name**, not a tag
separator. Only `:` introduces a tag:

```python
md.ModelRef.parse("qwen/qwen3-4b")        # name="qwen/qwen3-4b", tag="latest"
md.ModelRef.parse("qwen/qwen3-4b:q4_k_m") # name="qwen/qwen3-4b", tag="q4_k_m"
```

### Category installs query the Hugging Face Hub live

LM Studio's own local API exposes no searchable remote catalog, so there is
nothing on the LM Studio side to query. Instead, `install_category()` queries
the **Hugging Face Hub** directly for GGUF-tagged repositories — the same
place LM Studio's own model browser pulls from — and caches the result for 24
hours (`adapters/registry/huggingface_catalog.py`). This means the list of
suggested models grows and updates on its own; nothing needs to be
hand-maintained or shipped in a new ModelDock release for it to stay current.

Preview the list before committing to the downloads:

```python
mgr.suggest_category("coding")     # -> [ModelRef, ...], installs nothing
mgr.suggest_capability("vision")
```

When the Hub is unreachable and no cache exists yet (fully offline, first
run, no network), ModelDock falls back to a small curated list shipped in
`src/modeldock/adapters/runtimes/lmstudio_catalog.py`, so suggestions still
work with zero network access — just with a shorter, point-in-time list
instead of the live one.

Backends whose names already match the catalog (Ollama) are unaffected and
continue to install the full category.

### Downloads may need the desktop app

LM Studio manages model storage itself. ModelDock tries the local server's
download endpoint first; when that endpoint is unavailable the pull fails with
a message directing you to download the model in LM Studio's UI. This is a
property of LM Studio, not a ModelDock limitation.

Likewise, `remove()` attempts to unload the model and otherwise tells you to
remove it through the UI — the server does not expose a delete.

### The server must be running

Ollama runs as a background daemon; LM Studio's server is started explicitly
from the desktop app ("Developer" → "Start Server"). With it stopped,
`installed()` returns an empty list and `is_available()` is `False` rather than
raising, so discovery commands degrade instead of crashing.

See [Configuration](../user-guide/configuration.md) for how the server URL is
resolved and how to point ModelDock at a non-default host.

### Device reporting

`runtime_status().device` reports `unknown` on LM Studio. The server exposes no
VRAM or device metadata, so unlike Ollama there is nothing to infer GPU versus
CPU placement from.

## Capability mapping

| Category | Capabilities covered |
|---|---|
| `chat` | chat, completion, tool use |
| `coding` | chat, completion, tool use |
| `reasoning` | chat, completion, reasoning |
| `vision` | chat, vision |
| `embedding` | embed only |
| `instruct` | chat, completion |

Embedding models declare `embed` and nothing else — routing one into a chat
call fails at request time, so the mapping keeps them separate deliberately.
