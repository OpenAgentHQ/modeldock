"""ModelDock common utilities — config, logging, platform, http, errors."""

from modeldock.common.config import Settings, load_settings
from modeldock.common.errors import (
    AliasResolutionError,
    CacheError,
    ConfigError,
    DownloadError,
    ModelDockError,
    ModelNotFoundError,
    ModelNotInstalledError,
    RuntimeUnavailableError,
)
from modeldock.common.logging import configure_logging, get_logger
from modeldock.common.platform import (
    default_cache_dir,
    user_cache_dir,
    user_config_dir,
)

__all__ = [
    "Settings",
    "load_settings",
    "ModelDockError",
    "RuntimeUnavailableError",
    "ModelNotFoundError",
    "ModelNotInstalledError",
    "DownloadError",
    "CacheError",
    "ConfigError",
    "AliasResolutionError",
    "get_logger",
    "configure_logging",
    "default_cache_dir",
    "user_cache_dir",
    "user_config_dir",
]
