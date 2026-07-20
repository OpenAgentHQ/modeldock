# Roadmap

Current status and planned features.

---

## Current Status

ModelDock is in **active pre-release development** (v0.1.x).

| Component | Status |
|-----------|--------|
| Core architecture | Complete |
| Ollama runtime | Shipped |
| Dynamic catalog | Shipped |
| Python SDK | Shipped |
| CLI | Shipped |
| Smart caching | Shipped |

---

## Planned: Runtime Adapters

| Runtime | Status |
|---------|--------|
| Ollama | :material-check-circle:{ style="color: #4caf50" } Shipped |
| LM Studio | :material-clock-outline:{ style="color: #ff9800" } Planned |
| llama.cpp | :material-clock-outline:{ style="color: #ff9800" } Planned |
| Jan AI | :material-clock-outline:{ style="color: #ff9800" } Planned |
| GPT4All | :material-clock-outline:{ style="color: #ff9800" } Planned |
| vLLM | :material-clock-outline:{ style="color: #ff9800" } Planned |

---

## Planned: Features

- [ ] Automatic model downloads (default `auto_install` on)
- [ ] Searchable model registry from Python
- [ ] Bulk installation by category
- [ ] Model recommendations for beginners
- [ ] Download progress tracking (rich, tqdm, silent)
- [ ] Version management and updates
- [ ] Smart aliases (`load("llama3")`)
- [ ] Auto model selection based on task
- [ ] Offline cache management
- [ ] CLI completions
- [ ] Plugin hooks (EventPort lifecycle)

---

## Planned: Infrastructure

- [ ] Cross-platform CI (Windows/macOS/Linux × Python 3.9–3.12)
- [ ] Pre-commit hooks (ruff, mypy, bandit)
- [ ] Coverage reporting (≥80% target)
- [ ] PyPI publishing via trusted publishing
- [ ] Documentation site (MkDocs Material)

---

## Versioning

Following Semantic Versioning:

- **MAJOR** — Incompatible API changes
- **MINOR** — Backward-compatible new functionality
- **PATCH** — Backward-compatible bug fixes

---

## Links

- [GitHub Issues](https://github.com/OpenAgentHQ/modeldock/issues)
- [Changelog](changelog.md)
