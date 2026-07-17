"""CLI command: installed."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_installed
from modeldock.core.manager import ModelManager


def installed_cmd(
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """List locally installed models."""
    try:
        mgr = ModelManager()
        render_installed(mgr.installed())
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
