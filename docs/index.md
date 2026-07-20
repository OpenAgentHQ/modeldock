---
hide:
  - navigation
  - toc
---

# ModelDock

<div class="hero-banner" markdown>

### The package manager for local AI models

Lightweight. Python-first. Zero-config.

`md.load("llama3")` — and it just works.

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/OpenAgentHQ/modeldock){ .md-button }

</div>

---

## Why ModelDock?

Local LLMs are powerful, but managing them is painful. ModelDock eliminates the friction of discovering, downloading, organizing, and loading models — so you can focus on building.

<div class="feature-grid" markdown>

<div class="feature-card" markdown>

#### Python-First API

One line to load a model. No terminal commands, no searching model names, no repetitive downloads.

```python
import modeldock as md
client = md.load("llama3")
```

</div>

<div class="feature-card" markdown>

#### Auto-Install If Missing

`load()` checks if the model is installed, downloads it if not, verifies integrity, and returns a ready-to-use client.

```python
# Missing? Downloads automatically.
# Installed? Returns instantly.
client = md.load("llama3")
```

</div>

<div class="feature-card" markdown>

#### Searchable Registry

Browse models, categories, capabilities, and sizes without leaving Python. Dynamic catalog scraped from ollama.com.

```python
md.search("coding")
md.recommend(task="vision")
md.info("qwen3")
```

</div>

<div class="feature-card" markdown>

#### Bulk Installation

Install entire categories of models at once. Set up your coding workspace in one command.

```python
md.install_category("coding")
```

</div>

<div class="feature-card" markdown>

#### Smart Caching

Never re-download installed models. Content-addressed offline cache with 24-hour TTL.

```python
md.cache.status()
md.cache.clean()
```

</div>

<div class="feature-card" markdown>

#### Extensible Runtimes

Ollama ships first. LM Studio, llama.cpp, Jan AI, GPT4All, vLLM are drop-in adapters.

```python
client = md.load("llama3", backend="ollama")
```

</div>

</div>

---

## Architecture at a Glance

ModelDock follows **Clean Architecture** with SOLID principles. Dependencies point inward — the domain and ports layers are pure, concrete runtimes are adapters.

```
Interface:   modeldock/__init__.py (SDK)  +  modeldock/cli (Typer)
Application: modeldock/core/   (services, LifecycleOrchestrator, ModelManager)
Domain:      modeldock/domain/ (pure entities, no I/O)
Ports:       modeldock/ports/  (typing.Protocol interfaces)
Adapters:    modeldock/adapters/ (runtimes, registry, downloaders, cache, progress)
Common:      modeldock/common/ (config, logging, platform, http, errors)
```

---

## Quick Example

=== "Python SDK"

    ```python
    import modeldock as md

    # Auto-install if missing, then use
    client = md.load("llama3")

    # Run a chat
    response = client.chat(
        model="llama3",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response)
    ```

=== "CLI"

    ```bash
    # Load a model (auto-installs if missing)
    modeldock load llama3

    # Browse the catalog
    modeldock list

    # Search by capability
    modeldock search coding

    # Install specific models
    modeldock install llama3 qwen3 deepseek-r1
    ```

---

## Supported Runtimes

| Runtime    | Status | Notes |
|------------|--------|-------|
| Ollama     | :material-check-circle:{ style="color: #4caf50" } Shipped | First runtime, fully supported |
| LM Studio  | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| llama.cpp  | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| Jan AI     | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| GPT4All    | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| vLLM       | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |

---

## Install

```bash
pip install modeldock
# with the Ollama backend helper (optional):
pip install modeldock[ollama]
```

Requires **Python 3.9+** and a local [Ollama](https://ollama.com) install for the first runtime.

---

<div markdown style="text-align: center; margin-top: 2rem; opacity: 0.6;">

**ModelDock** is created and maintained by [Himanshu kumar](https://github.com/OpenAgentHQ) (OpenAgentHQ).

Licensed under MIT.

</div>
