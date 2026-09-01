"""Configuration model and loaders.

Precedence (low -> high): built-in defaults -> bundled catalog -> system config
-> user config -> env vars (MODELDOCK_*) -> explicit runtime overrides.
See Architecture.md §7. Invalid values fall back to defaults with a warning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
    ``validate_assignment`` is on so that values arriving from a config file or
    an environment variable are coerced and validated exactly like values passed
    to the constructor — otherwise ``default_backend`` would stay a raw ``str``
    and invalid levels/styles would be accepted silently.
    """

    model_config = ConfigDict(validate_assignment=True)

    default_backend: RuntimeBackend = RuntimeBackend.OLLAMA
    cache_dir: Path = Field(default_factory=default_cache_dir)
    registry_url: Optional[str] = None
    catalog_source: str = "auto"  # "auto" | "ollama" | "bundled"
    log_level: str = "ERROR"
    progress_style: str = "rich"
    auto_install: bool = False
    ollama_host: Optional[str] = None
    lmstudio_host: Optional[str] = None
    llamacpp_gpu_layers: Optional[int] = None
    gpt4all_models_dir: Optional[Path] = None
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

    @field_validator("llamacpp_gpu_layers", mode="before")
    @classmethod
    def _validate_llamacpp_gpu_layers(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Invalid llamacpp_gpu_layers {value!r}; expected an integer"
            ) from exc
        if parsed < -1:
            raise ConfigError(
                f"Invalid llamacpp_gpu_layers {parsed}; expected -1 (offload all layers) "
                "or a non-negative number of layers"
            )
        return parsed

    def to_env_overrides(self) -> Dict[str, str]:
        """Return the env-var form of these settings (for subprocess/debug)."""
        return {
            f"{_ENV_PREFIX}LOG_LEVEL": self.log_level,
            f"{_ENV_PREFIX}DEFAULT_BACKEND": self.default_backend.value,
            f"{_ENV_PREFIX}CATALOG_SOURCE": self.catalog_source,
            f"{_ENV_PREFIX}AUTO_INSTALL": str(self.auto_install).lower(),
            f"{_ENV_PREFIX}CACHE_DIR": str(self.cache_dir),
            f"{_ENV_PREFIX}GPT4ALL_MODELS_DIR": ""
            if self.gpt4all_models_dir is None
            else str(self.gpt4all_models_dir),
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


def _safe_set(settings: Settings, field: str, value: Any, source: str) -> None:
    """Assign ``field`` on ``settings``, warning and keeping the old value on error.

    Values from a config file or the environment must never crash the process:
    per the precedence contract, an invalid value falls back to whatever the
    lower-precedence layer resolved to, with a warning. Values passed
    programmatically still raise, because those come from the caller's own code.
    """
    try:
        setattr(settings, field, value)
    except (ValidationError, ConfigError) as exc:
        import logging

        logging.getLogger("modeldock").warning(
            "Ignoring invalid %s for %r (%s): %s", source, field, value, exc
        )


def _apply_mapping(settings: Settings, data: Dict[str, Any], source: str = "config value") -> None:
    """Apply a raw mapping onto ``settings`` with safe coercion."""
    if "default_backend" in data and data["default_backend"]:
        value = data["default_backend"]
        # Accept either a string or an already-resolved RuntimeBackend enum.
        try:
            resolved = (
                value
                if isinstance(value, RuntimeBackend)
                else RuntimeBackend.from_value(str(value))
            )
        except ValueError as exc:
            import logging

            logging.getLogger("modeldock").warning("Ignoring invalid %s: %s", source, exc)
        else:
            _safe_set(settings, "default_backend", resolved, source)
    if "cache_dir" in data and data["cache_dir"]:
        _safe_set(settings, "cache_dir", Path(str(data["cache_dir"])), source)
    if "registry_url" in data:
        _safe_set(settings, "registry_url", data["registry_url"] or None, source)
    if "catalog_source" in data and data["catalog_source"]:
        _safe_set(settings, "catalog_source", str(data["catalog_source"]), source)
    if "log_level" in data and data["log_level"]:
        _safe_set(settings, "log_level", _coerce_log_level(data["log_level"]), source)
    if "progress_style" in data and data["progress_style"]:
        _safe_set(settings, "progress_style", str(data["progress_style"]), source)
    if "auto_install" in data and data["auto_install"] is not None:
        _safe_set(settings, "auto_install", bool(data["auto_install"]), source)
    if "ollama_host" in data:
        _safe_set(settings, "ollama_host", data["ollama_host"] or None, source)
    if "lmstudio_host" in data:
        _safe_set(settings, "lmstudio_host", data["lmstudio_host"] or None, source)
    if "llamacpp_gpu_layers" in data:
        raw = data["llamacpp_gpu_layers"]
        _safe_set(settings, "llamacpp_gpu_layers", raw if raw not in (None, "") else None, source)
    if "gpt4all_models_dir" in data:
        raw = data["gpt4all_models_dir"]
        resolved_path = Path(str(raw)) if raw not in (None, "") else None
        _safe_set(settings, "gpt4all_models_dir", resolved_path, source)


def load_settings(
    explicit: Optional[Dict[str, Any]] = None,
    config_path: Optional[Path] = None,
) -> Settings:
    """Build a ``Settings`` from all precedence layers.

    ``explicit`` are runtime overrides applied last (highest precedence).
    """
    settings = Settings()

    # Lowest precedence first: files later in this list override earlier ones.
    # An explicit path is the caller's deliberate choice, so it comes last and
    # wins over the discovered system/user configs.
    candidates: list[Path] = []
    sys_cfg = system_config_dir() / "config.toml"
    user_cfg = user_config_dir() / "config.toml"
    for candidate in (sys_cfg, user_cfg):
        if candidate.exists():
            candidates.append(candidate)
    if config_path is not None:
        candidates.append(Path(config_path))

    for path in candidates:
        try:
            data = _toml_load(path)
        except Exception as exc:  # corrupt config -> warn, skip, never crash
            import logging

            logging.getLogger("modeldock").warning("Skipping config %s: %s", path, exc)
            continue
        _apply_mapping(settings, data, source=f"value in {path}")
        # Record the file whose values actually took effect, explicit or not.
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
        f"{_ENV_PREFIX}LMSTUDIO_HOST": "lmstudio_host",
        f"{_ENV_PREFIX}LLAMACPP_GPU_LAYERS": "llamacpp_gpu_layers",
        f"{_ENV_PREFIX}GPT4ALL_MODELS_DIR": "gpt4all_models_dir",
    }
    env_data = {
        field_name: os.environ[env_key]
        for env_key, field_name in env_map.items()
        if env_key in os.environ and os.environ[env_key]
    }
    if env_data:
        # Route env vars through the same coercion/validation as config files so
        # e.g. MODELDOCK_DEFAULT_BACKEND resolves to a RuntimeBackend instead of
        # staying a bare str, and an invalid level warns instead of sticking.
        _apply_mapping(settings, env_data, source=f"{_ENV_PREFIX}* environment variable")
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
