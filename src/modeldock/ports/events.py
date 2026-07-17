"""EventPort — lifecycle hooks for plugins/observers.

Pure interface. Implementations: a default no-op or user-supplied callbacks.
See Architecture.md §14 (plugin hooks).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from modeldock.domain.model import ModelRef


@runtime_checkable
class EventPort(Protocol):
    """Abstraction over lifecycle event hooks."""

    def before_pull(self, ref: ModelRef) -> None:
        """Called before a pull begins."""
        ...

    def after_install(self, ref: ModelRef, result: Any) -> None:
        """Called after a successful install."""
        ...

    def on_error(self, ref: ModelRef, error: Exception) -> None:
        """Called when an operation fails for ``ref``."""
        ...
