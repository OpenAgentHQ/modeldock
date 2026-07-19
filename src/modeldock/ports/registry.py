"""RegistryPort — the contract for a searchable model catalog.

Pure interface. Implementations: OllamaLibraryRegistry (live scraping),
BundledRegistry (static fallback). See Architecture.md §9.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from modeldock.domain.model import Category, ModelRef, ModelSpec


@runtime_checkable
class RegistryPort(Protocol):
    """Abstraction over a model registry/catalog."""

    def search(self, query: str) -> List[ModelSpec]:
        """Return specs whose name/alias/capability/category match ``query``."""
        ...

    def get(self, ref: ModelRef) -> ModelSpec:
        """Return the canonical spec for ``ref`` (raises if unknown)."""
        ...

    def by_category(self, category: Category) -> List[ModelSpec]:
        """Return all specs in a category."""
        ...

    def recommend(self, task: str) -> List[ModelSpec]:
        """Return specs recommended for a task (capability/category hint)."""
        ...

    def list_all(self) -> List[ModelSpec]:
        """Return every known spec."""
        ...
