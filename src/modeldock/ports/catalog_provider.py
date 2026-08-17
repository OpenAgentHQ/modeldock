"""CatalogProvider — the contract for a single online catalog source.

A ``RegistryPort`` implementation answers "what models do we know about" for
callers (search/get/recommend/...). A ``CatalogProvider`` is one layer below
that: it knows how to reach exactly one live, online source (ollama.com,
the Hugging Face Hub, ...) and turn what it finds into ``ModelSpec`` entries.

Splitting the two lets every new runtime reuse the same fetch → cache → index
pipeline (``adapters.registry.base.CachedCatalogRegistry``) instead of
reimplementing HTTP handling, disk caching, and RegistryPort plumbing from
scratch. See Architecture.md §9.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from modeldock.domain.model import ModelSpec, RuntimeBackend


@runtime_checkable
class CatalogProvider(Protocol):
    """Abstraction over a single live, online model-catalog source."""

    #: The runtime backend this provider's models are installed through.
    backend: RuntimeBackend

    def fetch(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch and parse raw model entries from the live source.

        Returns ``None`` on any network/parse failure so callers can fall
        back to a cache or a bundled catalog — never raises for ordinary
        connectivity issues.
        """
        ...

    def to_spec(self, raw: Dict[str, Any]) -> ModelSpec:
        """Convert one raw entry from :meth:`fetch` into a ``ModelSpec``."""
        ...


__all__ = ["CatalogProvider"]
