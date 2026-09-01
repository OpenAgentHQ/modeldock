"""Unit tests for CLI wiring: backend forwarding, update confirmation, config set."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pytest
from typer.testing import CliRunner

import modeldock.cli.commands.config as config_cmd
import modeldock.cli.factory as factory
from modeldock.cli.app import app
from modeldock.common.errors import ConfigError
from modeldock.domain.model import Category, ModelRef, RuntimeBackend

runner = CliRunner()


class _RecordingManager:
    """Stands in for ModelManager, recording how it was constructed."""

    last_backend: Optional[RuntimeBackend] = None

    def __init__(self, backend: Optional[RuntimeBackend] = None, **_: Any) -> None:
        type(self).last_backend = backend

    def install(self, name: str) -> ModelRef:
        return ModelRef.parse(name)

    def remove(self, name: str) -> None:
        return None

    def update(self, name: str, confirm: bool = False) -> ModelRef:
        if not confirm:
            raise AssertionError("update() must be called with confirm=True")
        return ModelRef.parse(name)


@pytest.fixture()
def recording_manager(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingManager]:
    _RecordingManager.last_backend = None
    monkeypatch.setattr(factory, "ModelManager", _RecordingManager)
    return _RecordingManager


# --- --backend forwarding --------------------------------------------------


def test_resolve_backend_accepts_known_value() -> None:
    assert factory.resolve_backend("lmstudio") is RuntimeBackend.LM_STUDIO


def test_resolve_backend_none_is_none() -> None:
    assert factory.resolve_backend(None) is None


def test_resolve_backend_rejects_unknown_value() -> None:
    with pytest.raises(ConfigError) as exc:
        factory.resolve_backend("nope")
    assert "supported backends" in str(exc.value)


def test_install_forwards_backend(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["install", "llama3", "--backend", "lmstudio"])
    assert result.exit_code == 0
    assert recording_manager.last_backend is RuntimeBackend.LM_STUDIO


def test_remove_forwards_backend(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["remove", "llama3", "--yes", "--backend", "vllm"])
    assert result.exit_code == 0
    assert recording_manager.last_backend is RuntimeBackend.VLLM


def test_omitted_backend_defers_to_config(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["install", "llama3"])
    assert result.exit_code == 0
    assert recording_manager.last_backend is None


def test_unknown_backend_exits_nonzero(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["install", "llama3", "--backend", "nope"])
    assert result.exit_code != 0
    assert "Unknown backend" in result.output


def test_install_category_help_includes_descriptions() -> None:
    result = runner.invoke(app, ["install-category", "--help"])
    output = " ".join(result.output.replace("│", " ").split())

    assert result.exit_code == 0
    for category in Category:
        assert category.value in output
        assert category.description in output


def test_global_backend_reaches_subcommands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODELDOCK_DEFAULT_BACKEND", raising=False)
    result = runner.invoke(app, ["--backend", "lmstudio", "config", "show"])
    assert result.exit_code == 0
    assert "default_backend: lmstudio" in result.output


# --- update confirmation ---------------------------------------------------


def test_update_with_yes_flag_confirms(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["update", "llama3", "--yes"])
    assert result.exit_code == 0
    assert "Updated llama3:latest" in result.output


def test_update_prompts_and_proceeds_on_yes(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["update", "llama3"], input="y\n")
    assert result.exit_code == 0
    assert "Updated llama3:latest" in result.output


def test_update_declined_does_nothing(recording_manager: type[_RecordingManager]) -> None:
    result = runner.invoke(app, ["update", "llama3"], input="n\n")
    assert result.exit_code == 0
    assert "Updated" not in result.output


# --- config set ------------------------------------------------------------


def test_config_set_preserves_existing_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("modeldock.common.platform.user_config_dir", lambda: tmp_path)
    cfg = tmp_path / "config.toml"
    cfg.write_text('cache_dir = "/data/models"\nollama_host = "http://box:11434"\n')

    config_cmd.config_set(key="log_level", value="DEBUG", debug=False)

    from modeldock.common.config import _toml_load

    data = _toml_load(cfg)
    assert data == {
        "cache_dir": "/data/models",
        "ollama_host": "http://box:11434",
        "log_level": "DEBUG",
    }


def test_config_set_updates_existing_key_in_place(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("modeldock.common.platform.user_config_dir", lambda: tmp_path)
    cfg = tmp_path / "config.toml"
    cfg.write_text('auto_install = true\nlog_level = "DEBUG"\n')

    config_cmd.config_set(key="auto_install", value="false", debug=False)

    from modeldock.common.config import _toml_load

    assert _toml_load(cfg) == {"auto_install": False, "log_level": "DEBUG"}


def test_config_set_creates_file_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "nested"
    monkeypatch.setattr("modeldock.common.platform.user_config_dir", lambda: target)

    config_cmd.config_set(key="log_level", value="INFO", debug=False)

    from modeldock.common.config import _toml_load

    assert _toml_load(target / "config.toml") == {"log_level": "INFO"}


def test_config_set_leaves_no_temp_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("modeldock.common.platform.user_config_dir", lambda: tmp_path)
    config_cmd.config_set(key="log_level", value="INFO", debug=False)
    assert [p.name for p in tmp_path.iterdir()] == ["config.toml"]
