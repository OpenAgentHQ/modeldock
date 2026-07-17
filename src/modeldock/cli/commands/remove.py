"""CLI command: remove."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager


def remove_cmd(
    models: list[str] = typer.Argument(..., help="Model name(s)"),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Uninstall model(s)."""
    try:
        mgr = ModelManager()
        for name in models:
            if not yes:
                confirm = typer.confirm(f"Remove {name}?")
                if not confirm:
                    continue
            mgr.remove(name)
            typer.echo(f"Removed {name}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
