"""Silent (no-op) progress reporter implementing ProgressPort (CI/headless)."""

from __future__ import annotations


class SilentProgress:
    """No-op progress reporter."""

    def start(self, total: int, desc: str = "") -> None:
        pass

    def update(self, advance: int) -> None:
        pass

    def finish(self, desc: str = "") -> None:
        pass


__all__ = ["SilentProgress"]
