# Using ModelDock with Ollama

ModelDock's first shipped runtime is **Ollama**. This guide shows how to drive
Ollama entirely through the ModelDock SDK — discover, install, load, run, and
manage models without touching the `ollama` CLI by hand.

> Prerequisites: Python 3.9–3.12 and a local [Ollama](https://ollama.com)
> install with the daemon running (`ollama serve`). Install the SDK with
> `pip install modeldock[ollama]` so the optional `ollama` client is available.

---

## Install

```bash
pip install modeldock
pip install modeldock[ollama]   # pulls in the ollama Python client
```

Ollama is the default backend, so you rarely need to name it explicitly.

---

## Load a model (auto-install)

`md.load()` returns a ready-to-use Ollama client. If the model isn't installed
locally, ModelDock installs it first (idempotently — already-installed models
are not re-downloaded).

```python
import modeldock as md

client = md.load("llama3")          # auto-installs if missing
client = md.load("llama3", backend="ollama")  # explicit backend
```

`load` is idempotent: calling it again for an installed model is instant.

---

## Discover and inspect

```python
md.list()                       # browse the bundled catalog
md.search("coding")             # search by name / capability / category
md.installed()                  # models already local (ModelRef list)
md.info("qwen3")                # sizes, capabilities, variants, installed tags
md.categories()                 # available categories
md.recommend(task="vision")     # guided pick
```

`md.installed()` and `md.info()` work even for models that aren't in the
bundled catalog, as long as they're installed in Ollama.

---

## Install explicitly

```python
md.install("llama3")                  # single model
md.install("llama3", backend="ollama")
md.install_category("coding")         # bulk install recommended models
```

---

## Run a completion / REPL

`md.run()` talks to the Ollama runtime. With a `prompt` it returns a single
completion; without one it drops into an interactive REPL.

```python
# Single completion
result = md.run("llama3", prompt="Explain semver in one sentence.")
print(result.text)

# Interactive REPL (reads stdin until you exit)
md.run("llama3")
```

Extra Ollama generation options are passed through:

```python
md.run("llama3", prompt="Hello", temperature=0.7, top_p=0.9)
```

---

## Update and remove

```python
md.update("llama3", confirm=True)   # removes then re-downloads — requires confirm
md.remove("llama3")                 # uninstall
md.verify("llama3")                 # integrity check -> bool
```

> `update()` is **destructive** (it deletes and re-pulls). It requires
> `confirm=True` and refuses cloud/subscription models.

---

## Cache management

```python
md.cache.status()    # list cache entries
md.cache.path()      # real cache directory
md.cache.clean()     # safe: removes only corrupt/partial entries
md.cache.clean(force=True)  # wipes everything
```

---

## Configuration

Override the singleton manager before first use:

```python
md.configure(
    ollama_host="http://localhost:11434",
    auto_install=True,
    log_level="INFO",
)
```

Or build an explicit, isolated manager:

```python
mgr = md.Manager(backend="ollama", ollama_host="http://localhost:11434")
mgr.load("llama3")
```

---

## Cloud / subscription models

Some catalog entries are **cloud/subscription** models — their tag contains
`cloud` (e.g. `glm-5.2:cloud`, `qwen3.5:397b-cloud`). These cannot be installed,
run, or removed through a local Ollama runtime. ModelDock short-circuits them
with a clear `DownloadError` instead of blocking on a daemon call:

```python
md.remove("glm-5.2:cloud")   # -> DownloadError: cloud/subscription model ...
md.update("glm-5.2:cloud", confirm=True)  # -> DownloadError (rejected)
```

---

## Runtime status

Check whether Ollama is reachable and on which device models execute:

```python
status = md._manager().runtime_status()
print(status.available, status.device)   # e.g. True, Device.CPU
```

`device` is `Device.GPU`, `Device.CPU`, or `Device.UNKNOWN`.

---

## Full example

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

See [`QUICKSTART.md`](../QUICKSTART.md) for the CLI equivalent and
[`Architecture.md`](../Architecture.md) for the design contract.
