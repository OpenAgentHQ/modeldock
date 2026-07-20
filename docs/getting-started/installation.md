# Installation

Multiple ways to install ModelDock.

---

## From PyPI

The recommended way:

```bash
pip install modeldock
```

With the Ollama backend helper (optional):

```bash
pip install modeldock[ollama]
```

---

## From Source

```bash
git clone https://github.com/OpenAgentHQ/modeldock.git
cd modeldock
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,ollama]"
```

---

## Prerequisites

- **Python 3.9+** (tested on 3.9, 3.10, 3.11, 3.12)
- A local [Ollama](https://ollama.com) install for the first runtime

---

## Development Install

For contributors who want the full dev setup:

```bash
git clone https://github.com/OpenAgentHQ/modeldock.git
cd modeldock
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ollama]"
pre-commit install
```

This installs:

- **Runtime dependencies:** `typer`, `httpx`, `pydantic`, `platformdirs`, `rich`, `tqdm`, `packaging`
- **Dev dependencies:** `pytest`, `pytest-cov`, `pytest-mock`, `ruff`, `mypy`, `bandit`, `pre-commit`
- **Ollama extras:** `ollama` Python client (optional)

---

## Verify Installation

```bash
python -c "import modeldock; print(modeldock.__version__)"
modeldock --version
modeldock --help
```

---

## Next Steps

- [First Model](first-model.md) — load your first model
- [Configuration](../user-guide/configuration.md) — customize ModelDock
