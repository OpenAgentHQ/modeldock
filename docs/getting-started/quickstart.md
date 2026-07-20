# Quickstart

Get ModelDock running in 30 seconds.

---

## Prerequisites

- **Python 3.9+**
- A local [Ollama](https://ollama.com) install with the daemon running (`ollama serve`)

---

## Install

```bash
pip install modeldock
# with the Ollama backend helper (optional):
pip install modeldock[ollama]
```

---

## 30-Second Start

```python
import modeldock as md

# Auto-installs if missing, then returns a ready-to-use client
client = md.load("llama3")

# Use it (runtime-native client, e.g. ollama.Client)
print(client.chat(model="llama3", messages=[{"role": "user", "content": "Hi!"}]))
```

That's it. No terminal commands, no searching model names.

---

## How `load()` Works

<div class="flow-diagram" markdown>
Model requested
    |
Already installed? ──yes──> return client
    | no
Download automatically (with progress)
    |
Verify installation (checksum + runtime check)
    |
Load model -> return ready client
</div>

Set `auto_install=True` in config to enable automatic downloads, or pass `backend="ollama"` to target a specific runtime.

---

## Common Commands

=== "Python"

    ```python
    import modeldock as md

    md.list()                       # browse the catalog
    md.search("coding")             # search by name / capability / category
    md.installed()                  # what's already local
    md.info("qwen3")                # sizes, capabilities, variants
    md.recommend(task="vision")     # guided pick

    md.install("llama3")            # explicit download
    md.install_category("coding")   # bulk install
    md.update("llama3")             # pull newer tag
    md.remove("llama3")             # uninstall
    md.verify("llama3")             # integrity check

    md.cache.status()               # what's cached
    md.cache.clean()                # drop orphans / partials
    ```

=== "CLI"

    ```bash
    modeldock load llama3
    modeldock install llama3 qwen3 deepseek-r1
    modeldock install-category coding
    modeldock list
    modeldock installed
    modeldock search vision
    modeldock info qwen3
    modeldock update llama3
    modeldock remove llama3
    modeldock cache status
    modeldock cache clean
    modeldock --help
    ```

Global flags: `--backend`, `--config-path`, `--log-level`, `--no-progress`, `--yes`.

---

## Next Steps

- [Installation](installation.md) — detailed install options
- [First Model](first-model.md) — load your first model step by step
- [User Guide](../user-guide/overview.md) — full feature reference
- [Architecture](../architecture/overview.md) — design contract
