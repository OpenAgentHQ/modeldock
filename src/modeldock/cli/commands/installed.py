"""CLI command: installed."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_installed, render_json
from modeldock.core.manager import ModelManager


def installed_cmd(
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """List locally installed models."""
    try:
        mgr = ModelManager()
        refs = mgr.installed()
        if json_out:
            render_json(refs)
        else:
            render_installed(refs)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug, as_json=json_out)
        raise typer.Exit(code=1)  # noqa: B904
