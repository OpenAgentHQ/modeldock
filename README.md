# ModelDock

> The lightweight, Python-first **model manager for local AI models** — the package manager for local LLMs.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![Release](https://github.com/OpenAgentHQ/modeldock/actions/workflows/release.yml/badge.svg)](https://github.com/OpenAgentHQ/modeldock/actions)

ModelDock discovers, downloads, caches, verifies, and loads local LLMs through
pluggable runtime adapters. It does **not** run inference itself; it orchestrates
runtimes (starting with Ollama). No more manual `ollama pull` commands — just
write `md.load("llama3")` and ModelDock handles the rest.

## Features

- **Python-first API** — `md.load("llama3")` auto-installs if missing and returns a ready client.
- **Searchable registry** — browse models, categories, capabilities, and sizes without leaving Python.
- **Bulk installation** — `md.install_category("coding")` pulls recommended models at once.
- **Smart caching** — never re-download installed models; content-addressed offline cache.
- **Extensible runtimes** — Ollama ships first; LM Studio, llama.cpp, Jan AI, GPT4All, vLLM are drop-in adapters.
- **Cross-platform** — Windows, macOS, Linux via `platformdirs`.
- **Zero-config, beginner-friendly** — works offline with a bundled catalog.

## Quick Start

### Prerequisites

- Python 3.10 or higher
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
Data:        modeldock/data/catalog.json (bundled model registry)
```

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

## Supported Runtimes

| Runtime | Status |
|---|---|
| Ollama | Shipped (first) |
| LM Studio, llama.cpp, Jan AI, GPT4All, vLLM | Planned adapters |

## Documentation

| File | Purpose |
|---|---|
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

## Support

- **Issues**: [GitHub Issues](https://github.com/OpenAgentHQ/modeldock/issues)
- **Documentation**: see the links above

See [SUPPORT.md](SUPPORT.md) for more options.

## Security

To report security vulnerabilities, see [SECURITY.md](SECURITY.md). Do not open
public issues for security problems.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.

## License

ModelDock is licensed under the Apache 2.0 License — see [LICENSE](LICENSE) for
details.
