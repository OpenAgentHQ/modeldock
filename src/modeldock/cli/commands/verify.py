"""CLI command: verify."""

from __future__ import annotations

import typer

from modeldock.cli.console import print_error, render_json, render_verify
from modeldock.cli.factory import manager_for


def verify_cmd(
    models: list[str] = typer.Argument(None, help="Model name(s) to verify"),
    all_: bool = typer.Option(False, "--all", help="Verify every installed model"),
    backend: str = typer.Option(None, "--backend", help="Runtime backend"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Verify installed model(s) integrity."""
    try:
        mgr = manager_for(backend)

        if all_:
            if models:
                raise typer.BadParameter("Cannot pass model names together with --all")
            names = [ref.name for ref in mgr.installed()]
        else:
            if not models:
                raise typer.BadParameter("Provide model name(s) or use --all")
            names = models

        results = [(name, mgr.verify(name)) for name in names]

        if json_out:
            render_json([{"name": name, "ok": ok} for name, ok in results])
        else:
            render_verify(results)

        if not all(ok for _, ok in results):
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug, as_json=json_out)
        raise typer.Exit(code=1)  # noqa: B904
