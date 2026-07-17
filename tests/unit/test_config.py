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


def test_default_cache_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODELDOCK_CACHE_DIR", str(tmp_path))
    assert default_cache_dir() == tmp_path


def test_is_windows_bool() -> None:
    assert isinstance(is_windows(), bool)
