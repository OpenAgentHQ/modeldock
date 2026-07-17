"""CLI command: config (show / set)."""

from __future__ import annotations

from typing import Any, Dict

import typer

from modeldock.cli.console import print_error
from modeldock.common.config import load_settings

config_app = typer.Typer(help="Configuration management")


@config_app.command("show")
def config_show(debug: bool = typer.Option(False, "--debug", help="Show traceback")) -> None:
    """Show the resolved configuration."""
    try:
        settings = load_settings()
        typer.echo(f"default_backend: {settings.default_backend.value}")
        typer.echo(f"cache_dir:       {settings.cache_dir}")
        typer.echo(f"registry_url:    {settings.registry_url}")
        typer.echo(f"log_level:       {settings.log_level}")
        typer.echo(f"progress_style:  {settings.progress_style}")
        typer.echo(f"auto_install:    {settings.auto_install}")
        typer.echo(f"ollama_host:     {settings.ollama_host}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Setting key"),
    value: str = typer.Argument(..., help="Setting value"),
    debug: bool = typer.Option(False, "--debug", help="Show traceback"),
) -> None:
    """Set a configuration value (writes user config.toml)."""
    try:
        from modeldock.common.platform import user_config_dir

        cfg_dir = user_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "config.toml"
        existing: Dict[str, Any] = {}
        if cfg_path.exists():
            import tomli

            with cfg_path.open("rb") as fh:
                existing = tomli.load(fh)
        existing[key] = value

        with cfg_path.open("w", encoding="utf-8") as fh:
            # TOML has no stdlib writer; emit a minimal valid TOML manually.
            fh.write(f"{key} = {_toml_scalar(value)}\n")
        typer.echo(f"Set {key} = {value} in {cfg_path}")
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print_error(exc, debug)
        raise typer.Exit(code=1)  # noqa: B904


def _toml_scalar(value: str) -> str:
    """Render a value as a TOML scalar literal."""
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered
    try:
        int(value)
        return value
    except ValueError:
        return f'"{value}"'
