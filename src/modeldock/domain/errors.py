"""Domain-layer exceptions.

Pure (no I/O, no framework). The application-wide ``ModelDockError`` hierarchy
lives in ``modeldock.common.errors``; domain errors are lightweight and used by
pure functions that must not import from ``common`` (which may touch config).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-layer errors."""


class AliasResolutionError(DomainError):
    """Raised when a friendly model name/tag cannot be resolved to a spec."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ModelSpecError(DomainError):
    """Raised when a model spec fails validation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


__all__ = ["DomainError", "AliasResolutionError", "ModelSpecError"]
