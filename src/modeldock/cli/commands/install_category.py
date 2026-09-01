"""CLI command: install-category."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.cli.factory import manager_for
from modeldock.domain.model import Category


def _category_help() -> str:
    """Build help text from the domain category descriptions."""
    descriptions = "; ".join(f"{item.value} ({item.description})" for item in Category)
    return f"Category name. Available: {descriptions}"


def install_category_cmd(
    category: str = typer.Argument(..., help=_category_help()),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Install every model in a category."""
    try:
        mgr = manager_for(backend)
        refs = mgr.install_category(category)
        for ref in refs:
            typer.echo(f"Installed {ref.qualified_name()}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
