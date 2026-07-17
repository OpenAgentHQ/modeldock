"""CLI command: info."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager


def info_cmd(
    model: str = typer.Argument(..., help="Model name"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Show model metadata, sizes, and capabilities."""
    try:
        mgr = ModelManager()
        spec = mgr.info(model)
        typer.echo(f"Name:        {spec.name}")
        typer.echo(f"Category:    {spec.category.value}")
        typer.echo(f"Capabilities:{', '.join(c.value for c in spec.capabilities)}")
        typer.echo(f"Default tag: {spec.default_tag}")
        typer.echo(f"Description: {spec.description}")
        if spec.variants:
            typer.echo("Variants:")
            for v in spec.variants:
                size = f"{v.size_bytes} bytes" if v.size_bytes else "?"
                ram = v.min_ram or "?"
                typer.echo(f"  - {v.tag} ({v.params or '?'}), {size}, min RAM {ram}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
