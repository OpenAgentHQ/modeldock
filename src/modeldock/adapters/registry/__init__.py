"""ModelDock registry adapters — dynamic Ollama catalog + bundled fallback."""

from modeldock.adapters.registry.bundled import BundledRegistry
from modeldock.adapters.registry.ollama_library import OllamaLibraryRegistry
from modeldock.adapters.registry.remote import RemoteRegistry

__all__ = ["BundledRegistry", "OllamaLibraryRegistry", "RemoteRegistry"]
