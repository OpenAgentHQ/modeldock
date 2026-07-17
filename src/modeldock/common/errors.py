"""ModelDock base error hierarchy.

Every error subclasses ``ModelDockError`` and carries actionable context.
Never raise a bare ``Exception`` — use one of these (or a subclass) so the
API/CLI can present a clear, friendly message. See Architecture.md §11.
"""

from __future__ import annotations


class ModelDockError(Exception):
    """Root of all ModelDock errors.

    Subclasses must provide a message that states what failed and the
    actionable next step.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class RuntimeUnavailableError(ModelDockError):
    """The requested runtime is not installed or not reachable."""

    def __init__(self, backend: str, hint: str = "") -> None:
        message = f"Runtime '{backend}' is not available or not running."
        if hint:
            message += f" {hint}"
        super().__init__(message)


class ModelNotFoundError(ModelDockError):
    """The model is not present in the registry/catalog."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Model '{name}' was not found in the registry. "
            f"Check the name or run `modeldock search` to browse available models."
        )


class ModelNotInstalledError(ModelDockError):
    """The model is not installed locally (with an auto-install hint)."""

    def __init__(self, name: str, auto_install: bool = False) -> None:
        if auto_install:
            super().__init__(
                f"Model '{name}' is not installed. It will be downloaded because "
                f"auto_install is enabled."
            )
        else:
            super().__init__(
                f"Model '{name}' is not installed. Run `modeldock install {name}` "
                f"or set auto_install=True."
            )


class DownloadError(ModelDockError):
    """A download/install failed (network, checksum, interrupted)."""

    def __init__(self, name: str, reason: str = "") -> None:
        message = f"Failed to download model '{name}'."
        if reason:
            message += f" Reason: {reason}"
        message += " Check your network connection and retry."
        super().__init__(message)


class CacheError(ModelDockError):
    """The cache manifest is corrupt or a cache operation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Cache error: {message}")


class ConfigError(ModelDockError):
    """A configuration value is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")


class AliasResolutionError(ModelDockError):
    """A friendly model alias could not be resolved to a spec."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Alias resolution error: {message}")


__all__ = [
    "ModelDockError",
    "RuntimeUnavailableError",
    "ModelNotFoundError",
    "ModelNotInstalledError",
    "DownloadError",
    "CacheError",
    "ConfigError",
    "AliasResolutionError",
]
