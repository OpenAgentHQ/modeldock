"""Cross-platform path and OS helpers.

Uses ``platformdirs`` for correct user/config/cache locations. No hardcoded
path separators. See Architecture.md §7.
"""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs


def app_name() -> str:
    """Return the application name used for platformdirs scopes."""
    return "modeldock"


def user_config_dir() -> Path:
    """Return the per-user config directory for ModelDock."""
    return Path(platformdirs.user_config_dir(app_name(), roaming=True))


def user_cache_dir() -> Path:
    """Return the per-user cache directory for ModelDock."""
    return Path(platformdirs.user_cache_dir(app_name()))


def user_data_dir() -> Path:
    """Return the per-user data directory for ModelDock."""
    return Path(platformdirs.user_data_dir(app_name()))


def system_config_dir() -> Path:
    """Return the system-wide config directory (may not exist)."""
    return Path(platformdirs.site_config_dir(app_name()))


def default_cache_dir() -> Path:
    """Return the default cache directory, honoring ``MODELDOCK_CACHE_DIR``."""
    override = os.environ.get("MODELDOCK_CACHE_DIR")
    if override:
        return Path(override)
    return user_cache_dir() / "models"


def is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt"


__all__ = [
    "app_name",
    "user_config_dir",
    "user_cache_dir",
    "user_data_dir",
    "system_config_dir",
    "default_cache_dir",
    "is_windows",
]
