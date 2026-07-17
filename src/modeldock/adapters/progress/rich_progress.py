"""Rich-based progress reporter implementing ProgressPort (lazy-imports rich)."""

from __future__ import annotations

from typing import Any, Optional


class RichProgress:
    """Rich-based progress bar reporter."""

    def __init__(self) -> None:
        self._progress: Optional[Any] = None
        self._task: Optional[Any] = None

    def start(self, total: int, desc: str = "") -> None:
        from rich.progress import Progress

        self._progress = Progress(transient=True)
        self._task = self._progress.add_task(desc or "Working", total=total or None)
        self._progress.start()

    def update(self, advance: int) -> None:
        if self._progress is not None and self._task is not None:
            self._progress.advance(self._task, advance)

    def finish(self, desc: str = "") -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
            self._task = None


__all__ = ["RichProgress"]
