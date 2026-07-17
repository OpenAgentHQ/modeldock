"""CLI command: list."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_models
from modeldock.core.manager import ModelManager


def list_cmd(debug: bool = typer.Option(False, "--debug", help="Show traceback")) -> None:
    """List all known catalog models."""
    try:
        mgr = ModelManager()
        render_models(mgr.list())
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
