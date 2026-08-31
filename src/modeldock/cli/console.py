"""Shared CLI output helpers (rich tables, JSON rendering, error formatting)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import Enum
from typing import Any, List

from pydantic import BaseModel

from modeldock.common.errors import ModelDockError


def to_jsonable(value: Any) -> Any:
    """Convert a domain object into JSON-safe primitives.

    Domain models are Pydantic v2, so ``model_dump(mode="json")`` already
    normalizes nested enums, paths, and optionals. Enums are checked *before*
    the primitive branch because ``Capability``/``Category``/``RuntimeBackend``
    subclass ``str`` — matching them as plain strings would emit the member
    repr instead of its ``.value``.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        # Normalize the key before coercing it: ``str()`` on a str-subclassing
        # enum yields the member repr, not its value.
        return {str(to_jsonable(key)): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    return str(value)


def render_json(payload: Any) -> None:
    """Print ``payload`` as indented JSON on stdout.

    Deliberately writes through ``sys.stdout`` rather than a rich ``Console``:
    rich wraps output at the terminal width, which would corrupt the document
    for the piped consumer this flag exists to serve.
    """
    import sys

    sys.stdout.write(json.dumps(to_jsonable(payload), indent=2) + "\n")


def print_error(exc: Exception, debug: bool = False, as_json: bool = False) -> None:
    """Print a friendly error to stderr; full traceback in debug mode.

    With ``as_json`` the error is emitted as a single JSON object so a script
    consuming ``--json`` can parse failures the same way it parses results.
    """
    import sys

    message = exc.message if isinstance(exc, ModelDockError) else str(exc)
    if as_json:
        payload = {"error": {"type": type(exc).__name__, "message": message}}
        sys.stderr.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stderr.write(f"Error: {message}\n")
    if debug:
        import traceback

        traceback.print_exc()


def render_models(models: List[Any]) -> None:
    """Render a list of ModelSpec as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Models")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Capabilities")
    table.add_column("Default Tag")
    table.add_column("Source")
    for spec in models:
        table.add_row(
            spec.name,
            spec.category.value,
            ", ".join(c.value for c in spec.capabilities),
            spec.default_tag,
            getattr(spec, "source", None) or "-",
        )
    console.print(table)


def render_installed(refs: List[Any]) -> None:
    """Render installed ModelRefs as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Installed Models")
    table.add_column("Name")
    table.add_column("Tag")
    table.add_column("Backend")
    for ref in refs:
        table.add_row(ref.name, ref.tag, ref.backend.value if ref.backend else "-")
    console.print(table)


def render_runtimes(statuses: List[Any]) -> None:
    """Render RuntimeStatus rows as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Runtimes")
    table.add_column("Backend")
    table.add_column("Available")
    table.add_column("Device")
    table.add_column("Loaded Models")
    table.add_column("Details")
    for status in statuses:
        table.add_row(
            status.backend.value,
            "yes" if status.available else "no",
            status.device.value,
            ", ".join(status.loaded_models) or "-",
            status.details or "-",
        )
    console.print(table)


def render_sources(sources: List[Any]) -> None:
    """Render active model sources (SourceInfo) as a rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Model Sources")
    table.add_column("Source")
    table.add_column("Trust")
    table.add_column("Kind")
    table.add_column("Backend")
    table.add_column("Models", justify="right")
    table.add_column("Status")
    for info in sources:
        table.add_row(
            info.name,
            info.trust.value,
            "live" if info.live else "static",
            info.backend.value if info.backend else "-",
            str(info.model_count),
            "ready" if info.available else "empty",
        )
    console.print(table)


__all__ = [
    "print_error",
    "render_installed",
    "render_json",
    "render_models",
    "render_runtimes",
    "render_sources",
    "to_jsonable",
]
