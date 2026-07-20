# Error Handling

ModelDock uses typed errors with actionable context. Never silent swallowing.

---

## Error Hierarchy

All exceptions subclass `ModelDockError` (in `common/errors.py`):

```
ModelDockError
├── RuntimeUnavailableError    # runtime not installed/running
├── ModelNotFoundError         # not in registry
├── ModelNotInstalledError     # missing locally, with auto_install hint
├── DownloadError              # network, checksum mismatch, interrupted
├── CacheError                 # corrupt manifest, permission denied
├── ConfigError                # invalid setting
└── AliasResolutionError       # alias could not be resolved
```

---

## Principles

### Fail-Fast, Clear Messages

Every error carries actionable context:

```
Model 'llama3' not installed. Run `modeldock install llama3` or set auto_install=True.
```

### No Silent Swallowing

Expected failure paths raise typed errors the API/CLI can catch and present nicely. Never `except: pass`.

### Typed Context

Every error includes:

- What failed
- Why it failed
- What to do next

---

## Checksum Verification

Downloads validated against expected SHA-256. Mismatch raises `DownloadError` with retry suggestion — never install corrupt weights.

---

## Retry Policy

Transient network errors retried with exponential backoff (configurable), then surface a clean error.

---

## CLI Mapping

Typed errors → friendly stderr messages + non-zero exit codes. `--debug` reveals full tracebacks.

---

## Writing Typed Errors

```python
from modeldock.common.errors import ModelDockError, DownloadError

class CustomError(ModelDockError):
    """Raised when something specific goes wrong."""

    def __init__(self, model: str, reason: str) -> None:
        super().__init__(
            f"Failed to process model '{model}': {reason}. "
            f"Try running `modeldock verify {model}` to check integrity."
        )
```

---

## Next Steps

- [Architecture Overview](overview.md) — design decisions
- [Clean Architecture](clean-architecture.md) — dependency rules
