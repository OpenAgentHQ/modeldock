"""ModelDock — lightweight, Python-first model manager for local LLMs.

Public API surface. Keep this narrow and stable; internals evolve behind ports.
See Architecture.md §5 and QUICKSTART.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__version__ = "0.1.3"
__author__ = "Himanshu kumar"

from modeldock.common.config import Settings
from modeldock.core.manager import ModelManager
from modeldock.domain.model import Category, ModelRef, RuntimeBackend

_MANAGER: Optional[ModelManager] = None


def _manager() -> ModelManager:
    """Return the lazy singleton ModelManager."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ModelManager()
    return _MANAGER


def configure(
    backend: Optional[str] = None,
    auto_install: Optional[bool] = None,
    log_level: Optional[str] = None,
    progress_style: Optional[str] = None,
    cache_dir: Optional[str] = None,
    ollama_host: Optional[str] = None,
) -> None:
    """Override configuration for the singleton manager."""
    global _MANAGER
    overrides: Dict[str, Any] = {}
    if backend is not None:
        overrides["default_backend"] = RuntimeBackend.from_value(backend)
    if auto_install is not None:
        overrides["auto_install"] = auto_install
    if log_level is not None:
        overrides["log_level"] = log_level
    if progress_style is not None:
        overrides["progress_style"] = progress_style
    if cache_dir is not None:
        overrides["cache_dir"] = cache_dir
    if ollama_host is not None:
        overrides["ollama_host"] = ollama_host
    _MANAGER = ModelManager(settings=Settings(**overrides))


def load(name: str, backend: Optional[str] = None, auto_install: Optional[bool] = None) -> Any:
    """Auto-install if missing, then return a ready-to-use client."""
    if backend is not None:
        return Manager(backend=backend).load(name, auto_install=auto_install)
    return _manager().load(name, auto_install=auto_install)


def list() -> List[Any]:
    """Browse the catalog."""
    return _manager().list()


def search(query: str) -> List[Any]:
    """Search by name / capability / category."""
    return _manager().search(query)


def installed() -> List[ModelRef]:
    """What's already local."""
    return _manager().installed()


def info(name: str) -> Any:
    """Sizes, capabilities, variants."""
    return _manager().info(name)


def categories() -> List[Category]:
    """Available categories."""
    return _manager().categories()


def recommend(task: str) -> List[Any]:
    """Guided pick for a task."""
    return _manager().recommend(task)


def install(name: str, backend: Optional[str] = None) -> ModelRef:
    """Explicit download."""
    if backend is not None:
        return Manager(backend=backend).install(name)
    return _manager().install(name)


def install_category(category: str, backend: Optional[str] = None) -> List[ModelRef]:
    """Bulk install by category."""
    if backend is not None:
        return Manager(backend=backend).install_category(category)
    return _manager().install_category(category)


def update(name: str, backend: Optional[str] = None, confirm: bool = False) -> ModelRef:
    """Pull a newer tag (destructive: removes then re-downloads)."""
    if backend is not None:
        return Manager(backend=backend).update(name, confirm=confirm)
    return _manager().update(name, confirm=confirm)


def remove(name: str, backend: Optional[str] = None) -> None:
    """Uninstall."""
    if backend is not None:
        Manager(backend=backend).remove(name)
        return
    _manager().remove(name)


def verify(name: str, backend: Optional[str] = None) -> bool:
    """Integrity check."""
    if backend is not None:
        return Manager(backend=backend).verify(name)
    return _manager().verify(name)


def run(name: str, prompt: Optional[str] = None, backend: Optional[str] = None, **opts: Any) -> Any:
    """Run an interactive session for a model in the active runtime.

    With ``prompt`` runs a single completion; without it, drops into a REPL.
    """
    if backend is not None:
        return Manager(backend=backend).run(name, prompt=prompt, **opts)
    return _manager().run(name, prompt=prompt, **opts)


class _CacheFacade:
    """Thin facade exposing cache operations on the singleton."""

    def status(self) -> List[Dict[str, Any]]:
        return _manager().cache.status()

    def clean(self) -> List[str]:
        return _manager().cache.clean()

    def path(self) -> str:
        return _manager().cache.path()


cache = _CacheFacade()


def Manager(
    backend: Optional[str] = None,
    auto_install: Optional[bool] = None,
    log_level: Optional[str] = None,
    progress_style: Optional[str] = None,
    cache_dir: Optional[str] = None,
    ollama_host: Optional[str] = None,
) -> ModelManager:
    """Create an explicit ModelManager instance."""
    overrides: Dict[str, Any] = {}
    if backend is not None:
        overrides["default_backend"] = RuntimeBackend.from_value(backend)
    if auto_install is not None:
        overrides["auto_install"] = auto_install
    if log_level is not None:
        overrides["log_level"] = log_level
    if progress_style is not None:
        overrides["progress_style"] = progress_style
    if cache_dir is not None:
        overrides["cache_dir"] = cache_dir
    if ollama_host is not None:
        overrides["ollama_host"] = ollama_host
    return ModelManager(settings=Settings(**overrides))


__all__ = [
    "load",
    "list",
    "search",
    "installed",
    "info",
    "categories",
    "recommend",
    "install",
    "install_category",
    "update",
    "remove",
    "verify",
    "run",
    "cache",
    "configure",
    "Manager",
    "ModelManager",
    "ModelRef",
    "RuntimeBackend",
    "Category",
]
