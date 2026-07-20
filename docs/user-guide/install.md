# Install & Manage

Download, update, and remove models.

---

## Install a Single Model

```python
import modeldock as md

md.install("llama3")
md.install("llama3", backend="ollama")  # explicit backend
```

---

## Install by Category

Bulk install recommended models for a specific use case:

```python
md.install_category("coding")
md.install_category("vision")
```

---

## Check What's Installed

```python
installed = md.installed()
# Returns list of ModelRef objects
```

---

## Update a Model

`update()` removes then re-downloads — it's destructive and requires confirmation:

```python
md.update("llama3", confirm=True)
```

!!! warning "Destructive Operation"
    `update()` deletes the model and re-pulls it. Always use `confirm=True`.
    Cloud/subscription models are rejected.

---

## Remove a Model

```python
md.remove("llama3")
```

---

## Verify Integrity

```python
result = md.verify("llama3")
# Returns True if model is intact
```

---

## Runtime Status

Check if the runtime is available and which device models execute on:

```python
status = md._manager().runtime_status()
print(status.available, status.device)  # True, Device.CPU
```

`device` is `Device.GPU`, `Device.CPU`, or `Device.UNKNOWN`.

---

## Next Steps

- [Load & Run](load.md) — load models and run completions
- [Cache Management](cache.md) — manage cached artifacts
