"""End-to-end CLI tests.

Exercises the Typer app via CliRunner for commands that don't require a runtime.
Commands needing Ollama (install/load/installed) are covered via the manager
unit tests and the integration layer; here we assert the CLI wiring + offline
commands work end to end. Marked `e2e` so they can be selected/skipped as a group.
"""

from __future__ import annotations

import logging

import pytest
from typer.testing import CliRunner

from modeldock.cli.app import app

pytestmark = pytest.mark.e2e

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "modeldock" in result.output.lower()


def test_cli_default_invocation_sets_error_level() -> None:
    # No --log-level -> callback resolves to the Typer default (ERROR) and does
    # not crash on an OptionInfo leaking through.
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert logging.getLogger("modeldock").level == logging.ERROR


def test_cli_no_arguments_shows_help() -> None:
    # `no_args_is_help` means bare invocation prints help. The exact exit code
    # differs across Typer/Click versions (0 or 2), so we assert the callback
    # ran and resolved options without an OptionInfo leaking through, and that
    # help text is present.
    result = runner.invoke(app, [])
    assert result.exit_code in (0, 2)
    assert "modeldock" in result.output.lower()


def test_cli_log_level_debug() -> None:
    result = runner.invoke(app, ["--log-level", "DEBUG", "list"])
    assert result.exit_code == 0
    assert logging.getLogger("modeldock").level == logging.DEBUG


def test_cli_invalid_log_level_falls_back_to_info() -> None:
    # Invalid level must not crash; callback coerces to INFO.
    result = runner.invoke(app, ["--log-level", "VERBOSE", "list"])
    assert result.exit_code == 0
    assert logging.getLogger("modeldock").level == logging.INFO


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "modeldock" in result.output.lower()


def test_cli_list_offline() -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    # Bundled catalog should list at least llama3.
    assert "llama3" in result.output


def test_cli_search_offline() -> None:
    result = runner.invoke(app, ["search", "coding"])
    assert result.exit_code == 0


def test_cli_info_offline() -> None:
    result = runner.invoke(app, ["info", "llama3"])
    assert result.exit_code == 0
    assert "llama3" in result.output


def test_cli_info_unknown_exits_nonzero() -> None:
    result = runner.invoke(app, ["info", "ghost-model"])
    assert result.exit_code != 0


def test_cli_info_renders_installed_section() -> None:
    result = runner.invoke(app, ["info", "llama3"])
    assert result.exit_code == 0
    assert "Installed:" in result.output
    assert "Variants:" in result.output


def test_cli_cache_status_offline() -> None:
    result = runner.invoke(app, ["cache", "status"])
    assert result.exit_code == 0


def test_cli_config_show_offline() -> None:
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "default_backend" in result.output


def test_cli_installed_offline_empty() -> None:
    # Offline behavior is environment-dependent but must never crash:
    # - SDK present, daemon down -> graceful empty list (exit 0)
    # - SDK missing -> actionable error surfaced (exit != 0, mentions install)
    result = runner.invoke(app, ["installed"])
    assert result.exit_code in (0, 1)
    if result.exit_code != 0:
        assert "modeldock[ollama]" in result.output


def test_cli_load_offline_errors() -> None:
    # `load` without a runtime/auto-install raises ModelNotInstalledError and
    # the CLI exits non-zero (expected offline behavior).
    result = runner.invoke(app, ["load", "llama3"])
    assert result.exit_code != 0


def test_cli_console_helpers() -> None:
    from modeldock.cli.console import print_error, render_installed, render_models
    from modeldock.common.errors import ModelNotFoundError
    from modeldock.domain.model import Category, ModelRef, ModelSpec

    print_error(ModelNotFoundError("x"))  # typed error path
    print_error(RuntimeError("boom"))  # generic error path
    render_models(
        [ModelSpec(name="llama3", category=Category.CHAT, capabilities=[], default_tag="latest")]
    )
    render_installed([ModelRef.parse("llama3")])
