"""ConfigService — application-layer access to Settings.

Thin facade over ``common.config.load_settings``. Keeps config resolution in
one place so core services depend on this, not on loaders directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from modeldock.common.config import Settings, load_settings


class ConfigService:
    """Provides resolved ``Settings`` to the rest of core."""

    def __init__(
        self,
        explicit: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self._settings = load_settings(explicit=explicit, config_path=config_path)

    @property
    def settings(self) -> Settings:
        """Return the resolved settings."""
        return self._settings

    def get(self, key: str) -> Any:
        """Return a single setting value by attribute name."""
        return getattr(self._settings, key)

    def update(self, **changes: Any) -> None:
        """Apply runtime overrides to the live settings."""
        for key, value in changes.items():
            setattr(self._settings, key, value)


__all__ = ["ConfigService"]
