"""CLI command: run."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager


def run_cmd(
    model: str = typer.Argument(..., help="Model name or name:tag"),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    prompt: str = typer.Option(None, "--prompt", help="Single prompt (skip interactive loop)"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Run an interactive session with a model, auto-installing if missing."""
    try:
        mgr = ModelManager()
        result = mgr.run(model, prompt=prompt)
        if hasattr(result, "success") and not result.success:
            print_error(Exception(result.error or "run failed"), debug)
            raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904


__all__ = ["run_cmd"]
