"""Unit tests for configuration loading and platform helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from modeldock.common.config import Settings, load_settings
from modeldock.common.errors import ConfigError
from modeldock.common.platform import default_cache_dir, is_windows
from modeldock.domain.model import RuntimeBackend


def test_settings_defaults() -> None:
    s = Settings()
    assert s.default_backend == RuntimeBackend.OLLAMA
    assert s.auto_install is False
    assert s.log_level == "ERROR"


def test_settings_validates_log_level() -> None:
    with pytest.raises(ConfigError):
        Settings(log_level="verbose")


def test_settings_validates_progress_style() -> None:
    with pytest.raises(ConfigError):
        Settings(progress_style="rainbow")


def test_settings_llamacpp_gpu_layers_defaults_to_none() -> None:
    assert Settings().llamacpp_gpu_layers is None


def test_settings_gpt4all_models_dir_defaults_to_none() -> None:
    assert Settings().gpt4all_models_dir is None


def test_settings_llamacpp_gpu_layers_accepts_non_negative_int() -> None:
    assert Settings(llamacpp_gpu_layers=35).llamacpp_gpu_layers == 35


def test_settings_llamacpp_gpu_layers_accepts_negative_one() -> None:
    assert Settings(llamacpp_gpu_layers=-1).llamacpp_gpu_layers == -1


def test_settings_llamacpp_gpu_layers_coerces_numeric_string() -> None:
    assert Settings(llamacpp_gpu_layers="42").llamacpp_gpu_layers == 42


def test_settings_llamacpp_gpu_layers_rejects_below_negative_one() -> None:
    with pytest.raises(ConfigError):
        Settings(llamacpp_gpu_layers=-2)


def test_settings_llamacpp_gpu_layers_rejects_non_integer() -> None:
    with pytest.raises(ConfigError):
        Settings(llamacpp_gpu_layers="auto")


def test_load_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELDOCK_DEFAULT_BACKEND", "vllm")
    monkeypatch.setenv("MODELDOCK_AUTO_INSTALL", "true")
    s = load_settings()
    assert s.default_backend == RuntimeBackend.VLLM
    assert s.auto_install is True


def test_load_settings_explicit_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELDOCK_DEFAULT_BACKEND", "vllm")
    s = load_settings(explicit={"default_backend": RuntimeBackend.OLLAMA})
    assert s.default_backend == RuntimeBackend.OLLAMA


def test_load_settings_cache_dir_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODELDOCK_CACHE_DIR", str(tmp_path / "models"))
    s = load_settings()
    assert s.cache_dir == tmp_path / "models"


def test_load_settings_llamacpp_gpu_layers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODELDOCK_LLAMACPP_GPU_LAYERS", "28")
    s = load_settings()
    assert s.llamacpp_gpu_layers == 28


def test_load_settings_llamacpp_gpu_layers_invalid_env_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODELDOCK_LLAMACPP_GPU_LAYERS", "auto")
    s = load_settings()
    assert s.llamacpp_gpu_layers is None


def test_load_settings_gpt4all_models_dir_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "gpt4all"
    monkeypatch.setenv("MODELDOCK_GPT4ALL_MODELS_DIR", str(models_dir))
    assert load_settings().gpt4all_models_dir == models_dir


def test_default_cache_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODELDOCK_CACHE_DIR", str(tmp_path))
    assert default_cache_dir() == tmp_path


def test_is_windows_bool() -> None:
    assert isinstance(is_windows(), bool)


# --- precedence and validation across layers -------------------------------


def _isolate_config_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the system/user config lookups at an empty temp dir."""
    user_dir = tmp_path / "user"
    user_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("modeldock.common.config.system_config_dir", lambda: tmp_path / "absent")
    monkeypatch.setattr("modeldock.common.config.user_config_dir", lambda: user_dir)
    return user_dir


def test_env_backend_resolves_to_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env values must be coerced like constructor values, not stored as str."""
    monkeypatch.setenv("MODELDOCK_DEFAULT_BACKEND", "lmstudio")
    s = load_settings()
    assert s.default_backend is RuntimeBackend.LM_STUDIO


def test_invalid_env_values_fall_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid env values warn and keep the lower-precedence value, never crash."""
    monkeypatch.setenv("MODELDOCK_LOG_LEVEL", "not-a-level")
    monkeypatch.setenv("MODELDOCK_CATALOG_SOURCE", "bogus")
    monkeypatch.setenv("MODELDOCK_PROGRESS_STYLE", "bogus")
    monkeypatch.setenv("MODELDOCK_DEFAULT_BACKEND", "nope")
    s = load_settings()
    assert s.log_level == "ERROR"
    assert s.catalog_source == "auto"
    assert s.progress_style == "rich"
    assert s.default_backend is RuntimeBackend.OLLAMA


def test_explicit_config_path_beats_user_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    user_dir = _isolate_config_dirs(monkeypatch, tmp_path)
    (user_dir / "config.toml").write_text(
        'log_level = "DEBUG"\nauto_install = true\nollama_host = "http://user:11434"\n'
    )
    explicit = tmp_path / "explicit.toml"
    explicit.write_text('log_level = "WARNING"\n')

    s = load_settings(config_path=explicit)

    assert s.log_level == "WARNING"  # explicit path wins
    assert s.auto_install is True  # keys it does not set still come from user config
    assert s.ollama_host == "http://user:11434"
    assert s.config_path == explicit


def test_sparse_explicit_overrides_preserve_other_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """configure(log_level=...) must not reset auto_install/ollama_host."""
    user_dir = _isolate_config_dirs(monkeypatch, tmp_path)
    (user_dir / "config.toml").write_text(
        'auto_install = true\nollama_host = "http://user:11434"\n'
    )

    overrides = Settings(log_level="INFO").model_dump(exclude_unset=True)
    s = load_settings(explicit=overrides)

    assert s.log_level == "INFO"
    assert s.auto_install is True
    assert s.ollama_host == "http://user:11434"


def test_toml_llamacpp_gpu_layers_applied(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user_dir = _isolate_config_dirs(monkeypatch, tmp_path)
    (user_dir / "config.toml").write_text("llamacpp_gpu_layers = 40\n")
    s = load_settings()
    assert s.llamacpp_gpu_layers == 40


def test_corrupt_config_is_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user_dir = _isolate_config_dirs(monkeypatch, tmp_path)
    (user_dir / "config.toml").write_text("this is not = valid = toml")
    assert load_settings().log_level == "ERROR"
