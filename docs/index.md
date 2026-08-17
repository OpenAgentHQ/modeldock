---
hide:
  - navigation
  - toc
---

<div class="hero-section" markdown>

<div class="hero-eyebrow" markdown>:material-tag-outline: v0.1.3 &nbsp;·&nbsp; MIT Licensed &nbsp;·&nbsp; Open Source</div>

# The package manager for local AI models

<p class="hero-sub" markdown>ModelDock discovers, downloads, caches, verifies, and loads local LLMs through pluggable runtime adapters. No more manual `ollama pull` — just `md.load("llama3")` and it just works.</p>

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/OpenAgentHQ/modeldock){ .md-button }

</div>

<div class="demo-frame" markdown>
<div class="demo-frame__titlebar">
  <span class="demo-frame__dot demo-frame__dot--red"></span>
  <span class="demo-frame__dot demo-frame__dot--yellow"></span>
  <span class="demo-frame__dot demo-frame__dot--green"></span>
</div>
![ModelDock demo: installing modeldock, loading a model with the Python SDK, and browsing models with the CLI](images/demo.gif)
</div>

## Get Started

<div class="card-grid card-grid--3" markdown>

<a class="doc-card" href="getting-started/quickstart/" markdown>
:material-rocket-launch-outline:{ .doc-card__icon }
<span class="doc-card__title">Quickstart</span>
<span class="doc-card__desc">Get ModelDock running in 30 seconds.</span>
<span class="doc-card__cta">Get started →</span>
</a>

<a class="doc-card" href="getting-started/installation/" markdown>
:material-download-outline:{ .doc-card__icon }
<span class="doc-card__title">Installation</span>
<span class="doc-card__desc">pip install, optional backend extras, and requirements.</span>
<span class="doc-card__cta">Get started →</span>
</a>

<a class="doc-card" href="getting-started/first-model/" markdown>
:material-play-circle-outline:{ .doc-card__icon }
<span class="doc-card__title">First Model</span>
<span class="doc-card__desc">Load, chat with, and manage your first local model.</span>
<span class="doc-card__cta">Get started →</span>
</a>

</div>

## Core Features

<div class="card-grid card-grid--3" markdown>

<a class="doc-card" href="sdk/python-api/" markdown>
:material-language-python:{ .doc-card__icon }
<span class="doc-card__title">Python-First API</span>
<span class="doc-card__desc">One line to load a model — <code>md.load("llama3")</code>. No terminal commands, no repetitive downloads.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

<a class="doc-card" href="user-guide/load/" markdown>
:material-cog-sync-outline:{ .doc-card__icon }
<span class="doc-card__title">Auto-Install If Missing</span>
<span class="doc-card__desc"><code>load()</code> checks, downloads, verifies, and returns a ready-to-use client.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

<a class="doc-card" href="user-guide/discover/" markdown>
:material-magnify:{ .doc-card__icon }
<span class="doc-card__title">Searchable Registry</span>
<span class="doc-card__desc">Browse models, categories, capabilities, and sizes without leaving Python.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

<a class="doc-card" href="user-guide/install/" markdown>
:material-archive-arrow-down-outline:{ .doc-card__icon }
<span class="doc-card__title">Bulk Installation</span>
<span class="doc-card__desc">Install entire categories of models at once — <code>md.install_category("coding")</code>.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

<a class="doc-card" href="user-guide/cache/" markdown>
:material-database-outline:{ .doc-card__icon }
<span class="doc-card__title">Smart Caching</span>
<span class="doc-card__desc">Never re-download installed models. Content-addressed offline cache.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

<a class="doc-card" href="architecture/runtime-adapters/" markdown>
:material-puzzle-outline:{ .doc-card__icon }
<span class="doc-card__title">Extensible Runtimes</span>
<span class="doc-card__desc">Ollama, LM Studio, and llama.cpp ship today; more are drop-in adapters.</span>
<span class="doc-card__cta">Learn more →</span>
</a>

</div>

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

## Supported Runtimes

| Runtime    | Status | Notes |
|------------|--------|-------|
| Ollama     | :material-check-circle:{ style="color: #0f9d8a" } Shipped | First runtime, fully supported |
| LM Studio  | :material-check-circle:{ style="color: #0f9d8a" } Shipped | OpenAI-compatible local server adapter |
| llama.cpp  | :material-check-circle:{ style="color: #0f9d8a" } Shipped | `llama-server` OpenAI-compatible adapter |
| Jan AI     | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| GPT4All    | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |
| vLLM       | :material-clock-outline:{ style="color: #ff9800" } Planned | Drop-in adapter |

## Resources

<div class="card-grid card-grid--3" markdown>

<a class="doc-card" href="architecture/overview/" markdown>
:material-sitemap-outline:{ .doc-card__icon }
<span class="doc-card__title">Architecture</span>
<span class="doc-card__desc">Clean Architecture design, ports/adapters, and how it all fits together.</span>
<span class="doc-card__cta">Read the docs →</span>
</a>

<a class="doc-card" href="contributing/guidelines/" markdown>
:material-account-group-outline:{ .doc-card__icon }
<span class="doc-card__title">Contributing</span>
<span class="doc-card__desc">Guidelines, dev setup, and how to add a new runtime adapter.</span>
<span class="doc-card__cta">Get involved →</span>
</a>

<a class="doc-card" href="https://github.com/OpenAgentHQ/modeldock" markdown>
:fontawesome-brands-github:{ .doc-card__icon }
<span class="doc-card__title">GitHub</span>
<span class="doc-card__desc">Source code, issues, and 100+ good-first-issues welcome.</span>
<span class="doc-card__cta">View repo →</span>
</a>

<a class="doc-card" href="https://pypi.org/project/modeldock/" markdown>
:material-package-variant-closed:{ .doc-card__icon }
<span class="doc-card__title">PyPI Package</span>
<span class="doc-card__desc"><code>pip install modeldock</code> — releases, versions, and downloads.</span>
<span class="doc-card__cta">View package →</span>
</a>

<a class="doc-card" href="project/changelog/" markdown>
:material-history:{ .doc-card__icon }
<span class="doc-card__title">Changelog</span>
<span class="doc-card__desc">What shipped, what changed, and what's next.</span>
<span class="doc-card__cta">See what's new →</span>
</a>

<a class="doc-card" href="project/security/" markdown>
:material-shield-check-outline:{ .doc-card__icon }
<span class="doc-card__title">Security</span>
<span class="doc-card__desc">Supported versions and how to report a vulnerability.</span>
<span class="doc-card__cta">Read more →</span>
</a>

</div>

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
