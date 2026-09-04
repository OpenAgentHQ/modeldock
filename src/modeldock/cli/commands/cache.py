"""CLI command: cache (status / clean / path)."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error
from modeldock.core.manager import ModelManager

cache_app = typer.Typer(help="Cache management")


@cache_app.command("status")
def cache_status(debug: bool = typer.Option(False, "--debug", help="Show traceback")) -> None:
    """Show cached model entries."""
    try:
        mgr = ModelManager()
        entries = mgr.cache.status()
        if not entries:
            typer.echo("Cache is empty.")
            return
        for e in entries:
            typer.echo(f"{e.get('name')}:{e.get('tag')} ({e.get('size_bytes')} bytes)")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904


@cache_app.command("clean")
def cache_clean(debug: bool = typer.Option(False, "--debug", help="Show traceback")) -> None:
    """Remove orphaned/partial artifacts."""
    try:
        mgr = ModelManager()
        removed = mgr.cache.clean()
        # clean() reports manifest entries as name:tag and reclaimed weights
        # as blobs/<sha256>; count them separately so the number means something.
        blobs = [item for item in removed if item.startswith("blobs/")]
        entries = len(removed) - len(blobs)
        typer.echo(f"Removed {entries} orphaned entries and {len(blobs)} unreferenced blobs.")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904


@cache_app.command("path")
def cache_path(debug: bool = typer.Option(False, "--debug", help="Show traceback")) -> None:
    """Show the cache directory path."""
    try:
        mgr = ModelManager()
        typer.echo(mgr.cache.path())
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904
