# Ollama Integration

ModelDock's first shipped runtime is Ollama. This guide covers the full integration.

---

## Prerequisites

- Python 3.9–3.12
- A local [Ollama](https://ollama.com) install with the daemon running (`ollama serve`)

```bash
pip install modeldock[ollama]   # pulls in the ollama Python client
```

---

## Load a Model

```python
import modeldock as md

client = md.load("llama3")          # auto-installs if missing
client = md.load("llama3", backend="ollama")  # explicit backend
```

`load` is idempotent — calling it again for an installed model is instant.

---

## Discover and Inspect

```python
md.list()                       # browse the catalog
md.search("coding")             # search by name / capability / category
md.installed()                  # models already local (ModelRef list)
md.info("qwen3")                # sizes, capabilities, variants, installed tags
md.categories()                 # available categories
md.recommend(task="vision")     # guided pick
```

`md.installed()` and `md.info()` work even for models not in the bundled catalog, as long as they're installed in Ollama.

---

## Install Explicitly

```python
md.install("llama3")                  # single model
md.install("llama3", backend="ollama")
md.install_category("coding")         # bulk install recommended models
```

---

## Run Completions / REPL

```python
# Single completion
result = md.run("llama3", prompt="Explain semver in one sentence.")
print(result.text)

# Interactive REPL (reads stdin until you exit)
md.run("llama3")
```

Pass Ollama generation options:

```python
md.run("llama3", prompt="Hello", temperature=0.7, top_p=0.9)
```

---

## Update and Remove

```python
md.update("llama3", confirm=True)   # removes then re-downloads — requires confirm
md.remove("llama3")                 # uninstall
md.verify("llama3")                 # integrity check -> bool
```

!!! warning "Destructive Operation"
    `update()` deletes and re-pulls. It requires `confirm=True` and refuses cloud/subscription models.

---

## Cache Management

```python
md.cache.status()    # list cache entries
md.cache.path()      # real cache directory
md.cache.clean()     # safe: removes only corrupt/partial entries
md.cache.clean(force=True)  # wipes everything
```

---

## Configuration

```python
md.configure(
    ollama_host="http://localhost:11434",
    auto_install=True,
    log_level="INFO",
)
```

Or build an explicit manager:

```python
mgr = md.Manager(backend="ollama", ollama_host="http://localhost:11434")
mgr.load("llama3")
```

---

## Cloud / Subscription Models

Some catalog entries are cloud/subscription models (tag contains `cloud`). These cannot be installed, run, or removed through a local Ollama runtime:

```python
md.remove("glm-5.2:cloud")   # -> DownloadError: cloud/subscription model ...
md.update("glm-5.2:cloud", confirm=True)  # -> DownloadError (rejected)
```

---

## Runtime Status

```python
status = md._manager().runtime_status()
print(status.available, status.device)   # True, Device.CPU
```

`device` is `Device.GPU`, `Device.CPU`, or `Device.UNKNOWN`.

---

## Full Example

```python
import modeldock as md

# 1. Make sure it's local (installs on first run)
client = md.load("llama3")

# 2. Run a completion
out = md.run("llama3", prompt="What is a package manager for LLMs?")
print(out.text)

# 3. Manage lifecycle
md.update("llama3", confirm=True)
md.remove("llama3")
```
