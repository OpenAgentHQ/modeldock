"""Focused coverage for shared HTTP, platform, and console helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modeldock.cli.console import (
    print_error,
    print_warning,
    render_installed,
    render_json,
    render_models,
    render_runtimes,
    render_sources,
    render_verify,
)
from modeldock.common.errors import ModelNotFoundError
from modeldock.common.http import create_async_client, create_client
from modeldock.common.platform import (
    app_name,
    default_cache_dir,
    is_windows,
    system_config_dir,
    user_cache_dir,
    user_config_dir,
    user_data_dir,
)
from modeldock.domain.model import (
    Capability,
    Category,
    Device,
    ModelInfo,
    ModelRef,
    ModelSpec,
    ModelVariant,
    RuntimeBackend,
    RuntimeStatus,
)
from modeldock.domain.source import SourceInfo, SourceTrust


def test_create_client_applies_defaults_and_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the synchronous client uses the default options and user agent."""
    factory = Mock(return_value=object())
    monkeypatch.setattr("modeldock.common.http.httpx.Client", factory)

    result = create_client()

    assert result is factory.return_value
    factory.assert_called_once_with(
        timeout=30.0,
        headers={"User-Agent": "modeldock/0.1.0"},
        verify=True,
        follow_redirects=True,
    )


def test_create_client_merges_custom_headers_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify custom synchronous client options override the defaults."""
    factory = Mock(return_value=object())
    monkeypatch.setattr("modeldock.common.http.httpx.Client", factory)

    create_client(timeout=4.5, headers={"X-Trace": "abc", "User-Agent": "custom"}, verify=False)

    factory.assert_called_once_with(
        timeout=4.5,
        headers={"User-Agent": "custom", "X-Trace": "abc"},
        verify=False,
        follow_redirects=True,
    )


def test_create_async_client_applies_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the asynchronous client uses the default options and user agent."""
    factory = Mock(return_value=object())
    monkeypatch.setattr("modeldock.common.http.httpx.AsyncClient", factory)

    result = create_async_client()

    assert result is factory.return_value
    factory.assert_called_once_with(
        timeout=30.0,
        headers={"User-Agent": "modeldock/0.1.0"},
        verify=True,
        follow_redirects=True,
    )


def test_create_async_client_merges_headers_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify custom asynchronous client options are merged with the defaults."""
    factory = Mock(return_value=object())
    monkeypatch.setattr("modeldock.common.http.httpx.AsyncClient", factory)

    create_async_client(timeout=8.0, headers={"Authorization": "Bearer token"}, verify=False)

    factory.assert_called_once_with(
        timeout=8.0,
        headers={"User-Agent": "modeldock/0.1.0", "Authorization": "Bearer token"},
        verify=False,
        follow_redirects=True,
    )


def test_app_name_uses_modeldock_scope() -> None:
    """Verify the application directory scope uses the ModelDock name."""
    assert app_name() == "modeldock"


def test_user_config_dir_uses_modeldock_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the user configuration directory is scoped to ModelDock."""
    lookup = Mock(return_value="/cfg")
    monkeypatch.setattr("modeldock.common.platform.platformdirs.user_config_dir", lookup)

    assert user_config_dir() == Path("/cfg")
    lookup.assert_called_once_with("modeldock", roaming=True)


def test_user_cache_dir_uses_modeldock_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the user cache directory is scoped to ModelDock."""
    lookup = Mock(return_value="/cache")
    monkeypatch.setattr("modeldock.common.platform.platformdirs.user_cache_dir", lookup)

    assert user_cache_dir() == Path("/cache")
    lookup.assert_called_once_with("modeldock")


def test_user_data_dir_uses_modeldock_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the user data directory is scoped to ModelDock."""
    lookup = Mock(return_value="/data")
    monkeypatch.setattr("modeldock.common.platform.platformdirs.user_data_dir", lookup)

    assert user_data_dir() == Path("/data")
    lookup.assert_called_once_with("modeldock")


def test_system_config_dir_uses_modeldock_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the system configuration directory is scoped to ModelDock."""
    lookup = Mock(return_value="/etc/modeldock")
    monkeypatch.setattr("modeldock.common.platform.platformdirs.site_config_dir", lookup)

    assert system_config_dir() == Path("/etc/modeldock")
    lookup.assert_called_once_with("modeldock")


def test_default_cache_dir_uses_environment_override(
    """Verify the cache directory environment override takes precedence."""
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    override = tmp_path / "custom-cache"
    monkeypatch.setenv("MODELDOCK_CACHE_DIR", str(override))

    assert default_cache_dir() == override


def test_default_cache_dir_uses_models_subdirectory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the default cache directory uses the models subdirectory."""
    monkeypatch.delenv("MODELDOCK_CACHE_DIR", raising=False)
    monkeypatch.setattr("modeldock.common.platform.user_cache_dir", lambda: Path("/cache"))

    assert default_cache_dir() == Path("/cache/models")


def test_is_windows_checks_platform_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Windows detection follows the platform name."""
    monkeypatch.setattr("modeldock.common.platform.os", SimpleNamespace(name="nt"))
    assert is_windows() is True

    monkeypatch.setattr("modeldock.common.platform.os", SimpleNamespace(name="posix"))
    assert is_windows() is False


def test_print_error_formats_modeldock_error_as_plain_text(
    """Verify ModelDock errors are printed as plain text to stderr."""
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_error(ModelNotFoundError("missing-model"))

    captured = capsys.readouterr()
    assert "Error: Model 'missing-model' was not found" in captured.err
    assert captured.out == ""


def test_print_error_emits_json_for_unknown_exception(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify unknown exceptions are serialized as JSON."""
    print_error(ValueError("bad value"), as_json=True)

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload == {"error": {"type": "ValueError", "message": "bad value"}}
    assert captured.out == ""


def test_print_error_includes_traceback_in_debug_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Include the active exception traceback when debug output is enabled."""
    try:
        raise ValueError("debug failure")
    except ValueError as error:
        print_error(error, debug=True)

    assert "Traceback (most recent call last)" in capsys.readouterr().err


def test_print_warning_writes_only_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify warnings are written to stderr without stdout output."""
    print_warning("review the selected backend")

    captured = capsys.readouterr()
    assert captured.err == "Warning: review the selected backend\n"
    assert captured.out == ""


def test_render_json_writes_indented_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify JSON rendering serializes domain objects with indentation."""
    spec = ModelSpec(
        name="llama3",
        category=Category.CHAT,
        capabilities=[Capability.CHAT],
        default_tag="8b",
        variants=[ModelVariant(tag="8b")],
    )
    info = ModelInfo.from_spec(spec, installed_tags=["8b"])
    render_json({"backend": RuntimeBackend.OLLAMA, "models": (spec, info)})

    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "ollama"
    assert payload["models"][0]["name"] == "llama3"
    assert payload["models"][1]["installed"] is True


def test_render_models_displays_catalog_fields(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify model rendering displays the catalog fields."""
    spec = ModelSpec(
        name="llama3",
        category=Category.CHAT,
        capabilities=[Capability.CHAT],
        default_tag="8b",
        variants=[ModelVariant(tag="8b")],
        source="ollama",
    )

    render_models([spec])

    output = capsys.readouterr().out
    assert "llama3" in output
    assert "chat" in output
    assert "ollama" in output


def test_render_installed_displays_backend(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify installed model rendering displays backend information."""
    render_installed([ModelRef(name="llama3", tag="8b", backend=RuntimeBackend.OLLAMA)])

    output = capsys.readouterr().out
    assert "llama3" in output
    assert "8b" in output
    assert "ollama" in output


def test_render_runtimes_displays_status_and_details(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify runtime rendering displays status and details."""
    statuses = [
        RuntimeStatus(
            backend=RuntimeBackend.OLLAMA,
            available=True,
            device=Device.GPU,
            loaded_models=["llama3:8b"],
            details="ready",
        ),
        RuntimeStatus(backend=RuntimeBackend.LM_STUDIO, available=False, device=Device.UNKNOWN),
    ]

    render_runtimes(statuses)

    output = capsys.readouterr().out
    assert "llama3:8b" in output
    assert "ready" in output
    assert "LM Studio" in output or "lmstudio" in output


def test_render_sources_displays_trust_and_availability(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify source rendering displays trust and availability."""
    sources = [
        SourceInfo(
            name="local-catalog",
            trust=SourceTrust.BUNDLED,
            live=False,
            backend=RuntimeBackend.OLLAMA,
            model_count=3,
            available=True,
        ),
        SourceInfo(
            name="remote-catalog",
            trust=SourceTrust.CUSTOM,
            live=True,
            model_count=0,
            available=False,
        ),
    ]

    render_sources(sources)

    output = capsys.readouterr().out
    assert "local-catalog" in output
    assert "remote-catalog" in output
    assert "bundled" in output
    assert "custom" in output


def test_render_verify_displays_success_and_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify verification rendering distinguishes successful and failed models."""
    render_verify([("llama3", True), ("qwen3", False)])

    output = capsys.readouterr().out
    assert "llama3" in output
    assert "qwen3" in output
    assert "OK" in output
    assert "FAILED" in output
