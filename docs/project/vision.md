# Vision

**ModelDock is the package manager for local AI models.**

---

## The Problem

Local LLMs are powerful, but managing them is painful. Developers must manually:

- Visit the Ollama website to find models
- Understand variants, sizes, tags
- Download each model individually
- Repeat for every new model
- Manage updates and storage

This interrupts development and creates unnecessary friction.

---

## The Solution

ModelDock provides a lightweight, Python-first interface for discovering, downloading, managing, caching, and loading local LLMs.

Instead of:

```bash
ollama pull llama3
ollama pull qwen3
ollama pull deepseek-r1
```

Just:

```python
import modeldock as md
client = md.load("llama3")
```

---

## Design Goals

- **Lightweight** — no bundled models, minimal dependencies
- **Python-first** — clean API, type hints everywhere
- **Beginner-friendly** — zero config, smart defaults
- **Smart caching** — never re-download installed models
- **Extensible** — new runtimes are drop-in adapters
- **Cross-platform** — Windows, macOS, Linux
- **Developer-focused** — fast, composable, predictable

---

## What ModelDock Is NOT

- It does **not** run inference
- It does **not** bundle models
- It does **not** replace Ollama — it orchestrates it

---

## Future Vision

- Automatic model downloads
- Searchable model registry from Python
- Bulk installation by category
- Model recommendations for beginners
- Download progress tracking
- Version management and updates
- Multiple runtime support (Ollama, LM Studio, llama.cpp, Jan AI, GPT4All, vLLM)
- Smart aliases (`load("llama3")`)

---

## Author

Created and maintained by **Himanshu kumar** ([OpenAgentHQ](https://github.com/OpenAgentHQ)).
