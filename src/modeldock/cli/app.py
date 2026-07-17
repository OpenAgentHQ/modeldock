"""ModelDock CLI — Typer application assembly.

Thin delivery layer: translates argv into core service calls. No business logic.
See Architecture.md §6.
"""

from __future__ import annotations

import typer

from modeldock.cli.commands.cache import cache_app
from modeldock.cli.commands.config import config_app
from modeldock.cli.commands.info import info_cmd
from modeldock.cli.commands.install import install_cmd
from modeldock.cli.commands.install_category import install_category_cmd
from modeldock.cli.commands.installed import installed_cmd
from modeldock.cli.commands.list import list_cmd
from modeldock.cli.commands.load import load_app
from modeldock.cli.commands.remove import remove_cmd
from modeldock.cli.commands.search import search_cmd
from modeldock.cli.commands.update import update_cmd
from modeldock.common.logging import configure_logging

app = typer.Typer(
    name="modeldock",
    help="ModelDock — the package manager for local AI models.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(load_app, name="load")
app.add_typer(cache_app, name="cache")
app.add_typer(config_app, name="config")
app.command("install")(install_cmd)
app.command("install-category")(install_category_cmd)
app.command("list")(list_cmd)
app.command("installed")(installed_cmd)
app.command("search")(search_cmd)
app.command("info")(info_cmd)
app.command("update")(update_cmd)
app.command("remove")(remove_cmd)


def _version_callback(value: bool) -> None:
    if value:
        from modeldock import __version__

        typer.echo(f"modeldock {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    log_level: str = typer.Option("ERROR", "--log-level", help="Log level"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable progress"),
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    """Global options applied before any subcommand."""
    configure_logging(level=log_level)
    if no_progress:
        import os

        os.environ["MODELDOCK_PROGRESS_STYLE"] = "silent"


def run() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    run()
