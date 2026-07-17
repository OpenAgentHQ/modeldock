"""CLI command: load."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager

load_app = typer.Typer()


@load_app.command("load")
def load_cmd(
    model: str = typer.Argument(..., help="Model name or name:tag"),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    tag: str = typer.Option("latest", "--tag", help="Model tag"),
    auto_install: bool = typer.Option(False, "--auto-install", help="Download if missing"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Load a model, auto-installing if missing."""
    try:
        mgr = ModelManager()
        name = f"{model}:{tag}" if tag != "latest" else model
        client = mgr.load(name, auto_install=auto_install)
        typer.echo(f"Loaded {name} -> {type(client).__name__}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
