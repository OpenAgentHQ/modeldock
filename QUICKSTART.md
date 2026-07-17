# Quickstart — ModelDock

> The lightweight, Python-first **model manager for local AI models**.
> Start with Ollama. Discover, download, cache, and load local LLMs with one line.

---

## Install

```bash
pip install modeldock
# with the Ollama backend helper (optional):
pip install modeldock[ollama]
```

Requires Python 3.9+ and a local [Ollama](https://ollama.com) install.

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

## Common Commands (Python)

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

---

## Common Commands (CLI)

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

## How `load()` Works

```
Model requested
   ↓
Already installed? ──yes──> return client
   ↓ no
Download automatically (with progress)
   ↓
Verify installation (checksum + runtime check)
   ↓
Load model → return ready client
```

Set `auto_install=True` in config to enable automatic downloads, or pass
`backend="ollama"` to target a specific runtime.

---

## Configuration

Config lives at `~/.config/modeldock/config.toml` (Linux/macOS) or
`%APPDATA%\modeldock\config.toml` (Windows). Env vars `MODELDOCK_*` override.

```toml
default_backend = "ollama"
auto_install    = true
log_level       = "INFO"
progress_style  = "rich"
```

Inspect or change it:

```bash
modeldock config show
modeldock config set auto_install true
```

---

## Supported Runtimes

| Runtime | Status |
|---|---|
| Ollama | ✅ Shipped |
| LM Studio | 🔜 Planned (adapter) |
| llama.cpp | 🔜 Planned (adapter) |
| Jan AI | 🔜 Planned (adapter) |
| GPT4All | 🔜 Planned (adapter) |
| vLLM | 🔜 Planned (adapter) |

New runtimes are drop-in adapters — no changes to your code.

---

## Next Steps

- Read [`PROJECT.MD`](./PROJECT.MD) for the full vision and pain points.
- Read [`Architecture.md`](./Architecture.md) for the design contract.
- Read [`AGENT.md`](./AGENT.md) if you're contributing or building agents here.
