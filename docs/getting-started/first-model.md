# First Model

Load your first model with ModelDock in three steps.

---

## Step 1: Ensure Ollama is Running

ModelDock orchestrates Ollama — it needs the daemon running:

```bash
ollama serve
```

Check it's working:

```bash
ollama list
```

---

## Step 2: Load a Model

```python
import modeldock as md

# This auto-installs if missing, then returns a ready client
client = md.load("llama3")
```

On first run, ModelDock will:

1. Check if `llama3` is installed locally
2. If not, download it from ollama.com (with progress bar)
3. Verify the installation
4. Return a ready-to-use client

---

## Step 3: Use It

The returned client is the native Ollama client — use it directly:

```python
# Chat
response = client.chat(
    model="llama3",
    messages=[{"role": "user", "content": "Explain Python decorators in one sentence."}]
)
print(response["message"]["content"])

# Or use md.run() for quick completions
result = md.run("llama3", prompt="What is a package manager for LLMs?")
print(result.text)
```

---

## That's It

`load()` is idempotent — calling it again for an installed model is instant.

```python
# First time: downloads (~4.7 GB for llama3:8b)
client = md.load("llama3")

# Second time: instant (already installed)
client = md.load("llama3")
```

---

## Next Steps

- [Discover Models](../user-guide/discover.md) — browse the catalog
- [Install & Manage](../user-guide/install.md) — manage multiple models
- [Load & Run](../user-guide/load.md) — advanced loading patterns
