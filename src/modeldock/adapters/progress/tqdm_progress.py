"""tqdm-based progress reporter implementing ProgressPort (lazy-imports tqdm)."""

from __future__ import annotations


class TqdmProgress:
    """tqdm-based progress bar reporter."""

    def __init__(self) -> None:
        self._bar = None

    def start(self, total: int, desc: str = "") -> None:
        from tqdm import tqdm

        self._bar = tqdm(total=total or None, desc=desc or "Working")

    def update(self, advance: int) -> None:
        if self._bar is not None:
            self._bar.update(advance)

    def finish(self, desc: str = "") -> None:
        if self._bar is not None:
            self._bar.close()
            self._bar = None


__all__ = ["TqdmProgress"]
