"""CLI command: info."""

from __future__ import annotations

from typing import Any

import typer

from modeldock.cli.console import print_error, render_json
from modeldock.core.manager import ModelManager


def _echo_spec(spec: Any) -> None:
    """Print a model spec as human-readable lines."""
    typer.echo(f"Name:        {spec.name}")
    typer.echo(f"Category:    {spec.category.value}")
    typer.echo(f"Capabilities:{', '.join(c.value for c in spec.capabilities)}")
    typer.echo(f"Default tag: {spec.default_tag}")
    typer.echo(f"Source:      {spec.source or '-'}")
    typer.echo(f"Description: {spec.description}")
    if spec.installed:
        typer.echo(f"Installed:   yes (tags: {', '.join(spec.installed_tags)})")
    else:
        typer.echo("Installed:   no")
    if spec.variants:
        typer.echo("Variants:")
        for v in spec.variants:
            size = f"{v.size_bytes} bytes" if v.size_bytes else "?"
            ram = v.min_ram or "?"
            typer.echo(f"  - {v.tag} ({v.params or '?'}), {size}, min RAM {ram}")


def info_cmd(
    model: str = typer.Argument(..., help="Model name"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Show model metadata, sizes, and capabilities."""
    try:
        mgr = ModelManager()
        spec = mgr.info(model)
        if json_out:
            render_json(spec)
        else:
            _echo_spec(spec)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug, as_json=json_out)
        raise typer.Exit(code=1)  # noqa: B904
