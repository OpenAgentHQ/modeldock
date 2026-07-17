"""ProgressPort — the contract for rendering download/install progress.

Pure interface. Implementations: RichProgress, TqdmProgress, SilentProgress.
See Architecture.md §10/§12. Progress goes through this port, never logging.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressPort(Protocol):
    """Abstraction over a progress reporter."""

    def start(self, total: int, desc: str = "") -> None:
        """Begin a progress unit with ``total`` bytes/steps."""
        ...

    def update(self, advance: int) -> None:
        """Advance progress by ``advance`` bytes/steps."""
        ...

    def finish(self, desc: str = "") -> None:
        """Mark the current progress unit complete."""
        ...
