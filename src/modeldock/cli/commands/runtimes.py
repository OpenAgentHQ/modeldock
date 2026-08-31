"""CLI command: runtimes."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_json, render_runtimes
from modeldock.core.manager import ModelManager


def runtimes_cmd(
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Show every registered runtime backend and whether it is reachable."""
    try:
        mgr = ModelManager()
        statuses = mgr.runtimes()
        if json_out:
            render_json(statuses)
        else:
            render_runtimes(statuses)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug, as_json=json_out)
        raise typer.Exit(code=1)  # noqa: B904
