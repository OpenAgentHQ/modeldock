"""CLI command: search."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_models
from modeldock.core.manager import ModelManager


def search_cmd(
    query: str = typer.Argument(..., help="Name / capability / category"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Search the catalog by name, capability, or category."""
    try:
        mgr = ModelManager()
        render_models(mgr.search(query))
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
