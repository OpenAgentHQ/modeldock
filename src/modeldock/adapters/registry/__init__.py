"""ModelDock registry adapters — bundled catalog + optional remote."""

from modeldock.adapters.registry.bundled import BundledRegistry
from modeldock.adapters.registry.remote import RemoteRegistry

__all__ = ["BundledRegistry", "RemoteRegistry"]
