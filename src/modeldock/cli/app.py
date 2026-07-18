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
from modeldock.cli.commands.run import run_cmd
from modeldock.cli.commands.search import search_cmd
from modeldock.cli.commands.update import update_cmd
from modeldock.common.logging import configure_logging

# Allowed log levels surfaced to the user via --help and validated in the CLI
# layer before any value reaches common/logging.configure_logging().
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

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
app.command("run")(run_cmd)


def _version_callback(value: bool) -> None:
    if value:
        from modeldock import __version__

        typer.echo(f"modeldock {__version__}")
        raise typer.Exit()


def _resolve_log_level(log_level: object) -> str:
    """Coerce the Typer option value to a valid level string for common/.

    Typer binds the resolved CLI value here, so ``log_level`` is normally a
    ``str``. If anything else (e.g. an ``OptionInfo`` descriptor from a direct
    call) leaks in, we normalize it to ``INFO`` at the CLI boundary so a
    framework object never propagates into ``common/``.
    """
    if not isinstance(log_level, str):
        return "INFO"
    normalized = log_level.strip().upper()
    if normalized not in _VALID_LOG_LEVELS:
        return "INFO"
    return normalized


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
    configure_logging(level=_resolve_log_level(log_level))
    if no_progress:
        import os

        os.environ["MODELDOCK_PROGRESS_STYLE"] = "silent"


def run() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    run()
