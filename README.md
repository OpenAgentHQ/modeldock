<p align="center">
  <img src="docs/images/modeldock.png" alt="ModelDock" width="420">
</p>

<h1 align="center">ModelDock</h1>

<p align="center">
  The lightweight, Python-first <strong>model manager for local AI models</strong> — the package manager for local LLMs.
</p>

<p align="center">
  <a href="https://github.com/OpenAgentHQ/modeldock/actions/workflows/check.yml"><img src="https://github.com/OpenAgentHQ/modeldock/actions/workflows/check.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/actions/workflows/check.yml"><img src="https://github.com/OpenAgentHQ/modeldock/actions/workflows/check.yml/badge.svg?event=push&name=Analyze%20(CodeQL)" alt="CodeQL"></a>
  <a href="https://codecov.io/gh/OpenAgentHQ/modeldock"><img src="https://codecov.io/gh/OpenAgentHQ/modeldock/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/pulls"><img src="https://img.shields.io/github/issues-pr/OpenAgentHQ/modeldock" alt="PRs"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/network/members"><img src="https://img.shields.io/github/forks/OpenAgentHQ/modeldock" alt="Forks"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/stargazers"><img src="https://img.shields.io/github/stars/OpenAgentHQ/modeldock" alt="Stars"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/graphs/contributors"><img src="https://img.shields.io/github/contributors/OpenAgentHQ/modeldock" alt="Contributors"></a>
  <a href="https://github.com/OpenAgentHQ/modeldock/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg" alt="Python"></a>
  <a href="https://pypi.org/project/modeldock/"><img src="https://img.shields.io/pypi/v/modeldock.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/modeldock/"><img src="https://img.shields.io/pypi/dm/modeldock.svg" alt="Downloads"></a>
  <a href="https://pypi.org/project/modeldock/"><img src="https://img.shields.io/badge/PyPI-modeldock-blue" alt="PyPI"></a>

  <a href="https://pepy.tech/projects/modeldock"><img src="https://static.pepy.tech/personalized-badge/modeldock?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads" alt="PyPI Downloads"></a>
</p>

---

ModelDock discovers, downloads, caches, verifies, and loads local LLMs through
pluggable runtime adapters. It does **not** run inference itself; it orchestrates
runtimes (starting with Ollama). No more manual `ollama pull` commands — just
write `md.load("llama3")` and ModelDock handles the rest.

<p align="center">
  <img src="docs/images/demo.gif" alt="ModelDock demo: installing modeldock, loading a model with the Python SDK, and browsing models with the CLI" width="720">
</p>

## Features

- **Python-first API** — `md.load("llama3")` auto-installs if missing and returns a ready client.
- **Searchable registry** — browse models, categories, capabilities, and sizes without leaving Python.
- **Bulk installation** — `md.install_category("coding")` pulls recommended models at once.
- **Smart caching** — never re-download installed models; content-addressed offline cache.
- **Extensible runtimes** — Ollama ships first; LM Studio, llama.cpp, Jan AI, GPT4All, vLLM are drop-in adapters.
- **Cross-platform** — Windows, macOS, Linux via `platformdirs`.
- **Zero-config, beginner-friendly** — dynamic catalog from ollama.com with offline caching.

## Quick Start

### Prerequisites

- Python 3.9–3.12
- A local [Ollama](https://ollama.com) install (for the first runtime)

### Installation

```bash
pip install modeldock
# with the Ollama backend helper (optional):
pip install modeldock[ollama]
```

### Basic Usage

```python
import modeldock as md

# Auto-installs if missing, then returns a ready-to-use client
client = md.load("llama3")

print(client.chat(model="llama3", messages=[{"role": "user", "content": "Hi!"}]))
```

## Installation

### From PyPI

```bash
pip install modeldock
```

### From Source

```bash
git clone https://github.com/OpenAgentHQ/modeldock.git
cd modeldock
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,ollama]"
```

## Usage

### Discover and manage models

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
```

### Command line

```bash
modeldock load llama3
modeldock install-category coding
modeldock list
modeldock search vision
modeldock cache status
```

See [QUICKSTART.md](QUICKSTART.md) for the full CLI/SDK reference.

## Architecture

ModelDock follows Clean Architecture with SOLID principles. Dependencies point
inward: `cli` → `core` → `ports` ← `adapters`. The `domain` and `ports` layers
are pure (no I/O); concrete runtimes implement the `RuntimePort` protocol.

```
Interface:   modeldock/__init__.py (SDK)  +  modeldock/cli (Typer)
Application: modeldock/core/   (services, LifecycleOrchestrator, ModelManager)
Domain:      modeldock/domain/ (pure entities, no I/O)
Ports:       modeldock/ports/  (typing.Protocol interfaces)
Adapters:    modeldock/adapters/ (runtimes, registry, downloaders, cache, progress)
Common:      modeldock/common/ (config, logging, platform, http, errors)
```

### Catalog Source

ModelDock scrapes `ollama.com/library` for a live model catalog, cached locally
for 24 hours. Set `catalog_source` in config or `MODELDOCK_CATALOG_SOURCE` env var:

| Value | Behavior |
|-------|----------|
| `auto` | Try dynamic, fallback to bundled; merges `registry_url` when set (default) |
| `ollama` | Dynamic only — requires internet |
| `bundled` | Static catalog.json only — fully offline |
| `remote` | `registry_url` only, merged over bundled — requires `registry_url` |

Set `registry_url` to a `catalog.json`-shaped URL to pick up models published
since the last release. Its entries are merged over the bundled catalog (never
replacing it) and cached for an hour; `modeldock sources refresh` re-fetches.

See [Architecture.md](Architecture.md) for the full design contract.

## Configuration

Config lives at `~/.config/modeldock/config.toml` (Linux/macOS) or
`%APPDATA%\modeldock\config.toml` (Windows). Env vars `MODELDOCK_*` override.

```toml
default_backend = "ollama"
auto_install    = true
log_level       = "INFO"
progress_style  = "rich"
```

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELDOCK_LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `ERROR` |
| `MODELDOCK_DEFAULT_BACKEND` | Runtime backend | `ollama` |
| `MODELDOCK_AUTO_INSTALL` | Auto-download missing models | `false` |
| `MODELDOCK_CACHE_DIR` | Override cache location | platform default |
| `MODELDOCK_OLLAMA_HOST` | Ollama server base URL | auto-discovered |
| `MODELDOCK_LMSTUDIO_HOST` | LM Studio server base URL | auto-discovered |
| `MODELDOCK_LLAMACPP_GPU_LAYERS` | GPU layers to offload for llama.cpp | unset |

### Runtime server URLs

Runtimes that talk to a local server resolve their base URL in this order:

1. `ollama_host` / `lmstudio_host` in `config.toml`
2. `MODELDOCK_OLLAMA_HOST` / `MODELDOCK_LMSTUDIO_HOST`
3. The runtime's own convention — `OLLAMA_HOST`, `LM_STUDIO_HOST`
4. **Auto-discovery** — the first address that answers: `localhost`, `127.0.0.1`,
   then `host.docker.internal` (so a container reaches a server on the host)
5. The documented default (`http://localhost:11434`, `http://localhost:1234`)

Discovery only runs when nothing is configured, so naming a host costs no
probing. URLs are normalized: `localhost:1234`, a trailing slash, and the
`/v1`-suffixed URL LM Studio's UI displays are all accepted.

### llama.cpp GPU layers

`llama-server` binds one already-running process and has no API to report or
change how many layers it offloaded to the GPU — that's a launch-time `-ngl`
flag, not something a client can query or set afterwards. ModelDock lets you
configure the value you use so every launch command it suggests (e.g. when
the server isn't running yet) includes it:

1. `llamacpp_gpu_layers` in `config.toml`
2. `MODELDOCK_LLAMACPP_GPU_LAYERS`
3. `LLAMA_ARG_N_GPU_LAYERS` — llama-server's own env var for `-ngl`
4. Unset — suggested commands omit `-ngl` entirely

```toml
llamacpp_gpu_layers = 35  # or -1 to offload all layers
```

## Supported Runtimes

| Runtime | Status |
|---|---|
| Ollama | ✅ Fully supported |
| LM Studio, llama.cpp, Jan AI, GPT4All, vLLM | Planned adapters |

## Documentation

| File | Purpose |
|------|---------|
| [PROJECT.MD](PROJECT.MD) | Product vision, pain points, roadmap |
| [Architecture.md](Architecture.md) | Design contract |
| [AGENT.md](AGENT.md) | Agent/contributor rules + coding standards |
| [QUICKSTART.md](QUICKSTART.md) | 30-second user start |
| [Development.md](Development.md) | Build, test, CI, release setup |
| [CONTEXT.md](CONTEXT.md) | Orientation hub |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | How to work in this repo |
| [RELEASE.md](RELEASE.md) | Release process |

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
branch naming, coding standards, and the PR process.

You can claim an issue to work on by commenting `/claim` on it — a maintainer
will assign it to you.

## Support

- **Issues**: [GitHub Issues](https://github.com/OpenAgentHQ/modeldock/issues)
- **Documentation**: see the links above

See [SUPPORT.md](SUPPORT.md) for more options.

## Security

To report security vulnerabilities, see [SECURITY.md](SECURITY.md). Do not open
public issues for security problems.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.

## Author

ModelDock is created and maintained by **Himanshu kumar** (OpenAgentHQ).

## License

ModelDock is licensed under the MIT License — see [LICENSE](LICENSE) for
details.
