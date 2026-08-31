"""CLI command: list."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_json, render_models
from modeldock.core.manager import ModelManager


def list_cmd(
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """List all known catalog models."""
    try:
        mgr = ModelManager()
        models = mgr.list()
        if json_out:
            render_json(models)
        else:
            render_models(models)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug, as_json=json_out)
        raise typer.Exit(code=1)  # noqa: B904
