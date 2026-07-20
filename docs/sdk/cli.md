# CLI Reference

All ModelDock CLI commands.

---

## Entry Point

```bash
modeldock
python -m modeldock
```

---

## Commands

### Load

```bash
modeldock load <model> [--backend ollama] [--tag 8b]
```

Auto-install if missing, then return a ready client.

---

### Install

```bash
modeldock install <model>...
```

Explicit download of one or more models.

---

### Install Category

```bash
modeldock install-category <category>
```

Bulk install recommended models for a category (e.g., `coding`, `vision`).

---

### List

```bash
modeldock list
```

Browse the catalog.

---

### Installed

```bash
modeldock installed
```

Models present locally.

---

### Search

```bash
modeldock search <query>
```

Search by name, capability, or category.

---

### Info

```bash
modeldock info <model>
```

Sizes, capabilities, variants.

---

### Recommend

```bash
modeldock recommend [--task coding]
```

Guided pick for a task.

---

### Update

```bash
modeldock update <model>...
```

Pull newer tag (destructive: removes then re-downloads).

---

### Remove

```bash
modeldock remove <model>...
```

Uninstall a model.

---

### Cache

```bash
modeldock cache status
modeldock cache clean
modeldock cache path
```

Manage the cache.

---

### Config

```bash
modeldock config show
modeldock config set <key> <value>
```

View or change configuration.

---

## Global Flags

| Flag | Description |
|------|-------------|
| `--backend` | Runtime backend |
| `--config-path` | Custom config file path |
| `--log-level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `--no-progress` | Disable progress bars |
| `--yes` | Skip confirmation prompts |
| `--version` | Show version |
| `--help` | Show help |

---

## Next Steps

- [Python API](python-api.md) — SDK reference
- [Configuration](../user-guide/configuration.md) — config options
