"""CLI command: update."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager


def update_cmd(
    models: list[str] = typer.Argument(..., help="Model name(s)"),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Pull a newer tag for installed model(s)."""
    try:
        mgr = ModelManager()
        for name in models:
            ref = mgr.update(name)
            typer.echo(f"Updated {ref.qualified_name()}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
