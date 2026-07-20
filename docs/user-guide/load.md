# Load & Run

Load models and run completions.

---

## Load a Model

The flagship operation — auto-installs if missing:

```python
import modeldock as md

client = md.load("llama3")
client = md.load("llama3", backend="ollama")  # explicit backend
```

---

## Use the Returned Client

The client is the native runtime client (e.g., `ollama.Client`). Use it directly:

```python
# Chat
response = client.chat(
    model="llama3",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Generate
response = client.generate(model="llama3", prompt="Once upon a time")
```

---

## Run Completions

Use `md.run()` for quick completions:

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

## Next Steps

- [Cache Management](cache.md) — manage cached artifacts
- [Configuration](configuration.md) — all config options
- [SDK Reference](../sdk/python-api.md) — full API reference
