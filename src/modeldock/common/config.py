"""Configuration model and loaders.

Precedence (low -> high): built-in defaults -> bundled catalog -> system config
-> user config -> env vars (MODELDOCK_*) -> explicit runtime overrides.
See Architecture.md §7. Invalid values fall back to defaults with a warning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from modeldock.common.errors import ConfigError
from modeldock.common.platform import (
    default_cache_dir,
    system_config_dir,
    user_config_dir,
)
from modeldock.domain.model import RuntimeBackend

_ENV_PREFIX = "MODELDOCK_"


class Settings(BaseModel):
    """Frozen-ish settings model for ModelDock.

    Mutable only via explicit ``update`` so precedence is controlled centrally.
    """

    default_backend: RuntimeBackend = RuntimeBackend.OLLAMA
    cache_dir: Path = Field(default_factory=default_cache_dir)
    registry_url: Optional[str] = None
    catalog_source: str = "auto"  # "auto" | "ollama" | "bundled"
    log_level: str = "ERROR"
    progress_style: str = "rich"
    auto_install: bool = False
    ollama_host: Optional[str] = None
    config_path: Optional[Path] = None

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.strip().upper()
        if upper not in allowed:
            raise ConfigError(f"Invalid log_level {value!r}; expected one of {sorted(allowed)}")
        return upper

    @field_validator("progress_style")
    @classmethod
    def _validate_progress_style(cls, value: str) -> str:
        allowed = {"rich", "tqdm", "silent"}
        if value not in allowed:
            raise ConfigError(
                f"Invalid progress_style {value!r}; expected one of {sorted(allowed)}"
            )
        return value

    @field_validator("catalog_source")
    @classmethod
    def _validate_catalog_source(cls, value: str) -> str:
        allowed = {"auto", "ollama", "bundled"}
        if value not in allowed:
            raise ConfigError(
                f"Invalid catalog_source {value!r}; expected one of {sorted(allowed)}"
            )
        return value

    def to_env_overrides(self) -> Dict[str, str]:
        """Return the env-var form of these settings (for subprocess/debug)."""
        return {
            f"{_ENV_PREFIX}LOG_LEVEL": self.log_level,
            f"{_ENV_PREFIX}DEFAULT_BACKEND": self.default_backend.value,
            f"{_ENV_PREFIX}CATALOG_SOURCE": self.catalog_source,
            f"{_ENV_PREFIX}AUTO_INSTALL": str(self.auto_install).lower(),
            f"{_ENV_PREFIX}CACHE_DIR": str(self.cache_dir),
        }


def _toml_load(path: Path) -> Dict[str, Any]:
    """Load a TOML file into a dict, using tomllib (3.11+) or tomli."""
    try:
        if hasattr(__import__("tomllib"), "load"):
            import tomllib

            with path.open("rb") as fh:
                return tomllib.load(fh)
    except ModuleNotFoundError:
        pass
    import tomli

    with path.open("rb") as fh:
        data: Dict[str, Any] = tomli.load(fh)
        return data


def _coerce_log_level(value: Any) -> str:
    return str(value).strip().upper()


def _apply_mapping(settings: Settings, data: Dict[str, Any]) -> None:
    """Apply a raw mapping onto ``settings`` with safe coercion."""
    if "default_backend" in data and data["default_backend"]:
        value = data["default_backend"]
        # Accept either a string or an already-resolved RuntimeBackend enum.
        settings.default_backend = (
            value if isinstance(value, RuntimeBackend) else RuntimeBackend.from_value(str(value))
        )
    if "cache_dir" in data and data["cache_dir"]:
        settings.cache_dir = Path(str(data["cache_dir"]))
    if "registry_url" in data:
        settings.registry_url = data["registry_url"] or None
    if "catalog_source" in data and data["catalog_source"]:
        settings.catalog_source = str(data["catalog_source"])
    if "log_level" in data and data["log_level"]:
        settings.log_level = _coerce_log_level(data["log_level"])
    if "progress_style" in data and data["progress_style"]:
        settings.progress_style = str(data["progress_style"])
    if "auto_install" in data and data["auto_install"] is not None:
        settings.auto_install = bool(data["auto_install"])
    if "ollama_host" in data:
        settings.ollama_host = data["ollama_host"] or None


def load_settings(
    explicit: Optional[Dict[str, Any]] = None,
    config_path: Optional[Path] = None,
) -> Settings:
    """Build a ``Settings`` from all precedence layers.

    ``explicit`` are runtime overrides applied last (highest precedence).
    """
    settings = Settings()

    candidates: list[Path] = []
    sys_cfg = system_config_dir() / "config.toml"
    user_cfg = user_config_dir() / "config.toml"
    if config_path is not None:
        candidates.append(Path(config_path))
    for candidate in (sys_cfg, user_cfg):
        if candidate.exists():
            candidates.append(candidate)

    for path in candidates:
        try:
            data = _toml_load(path)
        except Exception as exc:  # corrupt config -> warn, skip, never crash
            import logging

            logging.getLogger("modeldock").warning("Skipping config %s: %s", path, exc)
            continue
        _apply_mapping(settings, data)
        if config_path is None:
            settings.config_path = path

    # Env var overrides (MODELDOCK_*)
    env_map = {
        f"{_ENV_PREFIX}DEFAULT_BACKEND": "default_backend",
        f"{_ENV_PREFIX}CACHE_DIR": "cache_dir",
        f"{_ENV_PREFIX}REGISTRY_URL": "registry_url",
        f"{_ENV_PREFIX}CATALOG_SOURCE": "catalog_source",
        f"{_ENV_PREFIX}LOG_LEVEL": "log_level",
        f"{_ENV_PREFIX}PROGRESS_STYLE": "progress_style",
        f"{_ENV_PREFIX}OLLAMA_HOST": "ollama_host",
    }
    for env_key, field_name in env_map.items():
        if env_key in os.environ and os.environ[env_key]:
            raw = os.environ[env_key]
            # Coerce path-like fields so cache_dir is always a Path (consistent
            # with the config-file path, which uses Path(str(...))).
            coerced: Any = Path(raw) if field_name == "cache_dir" else raw
            setattr(settings, field_name, coerced)
    if f"{_ENV_PREFIX}AUTO_INSTALL" in os.environ:
        settings.auto_install = os.environ[f"{_ENV_PREFIX}AUTO_INSTALL"].lower() in {
            "1",
            "true",
            "yes",
        }

    if explicit:
        _apply_mapping(settings, explicit)

    return settings


__all__ = ["Settings", "load_settings"]
