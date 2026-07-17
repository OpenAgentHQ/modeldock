"""RegistryService — discovery over a RegistryPort.

Implements search/info/categories/recommend by composing the registry adapter.
See Architecture.md §9.
"""

from __future__ import annotations

from typing import List

from modeldock.domain.model import Category, ModelRef, ModelSpec
from modeldock.ports.registry import RegistryPort


class RegistryService:
    """Application service for model discovery."""

    def __init__(self, registry: RegistryPort) -> None:
        self._registry = registry

    def search(self, query: str) -> List[ModelSpec]:
        """Search the catalog by name/alias/capability/category."""
        return self._registry.search(query)

    def info(self, name: str) -> ModelSpec:
        """Return metadata for a model (raises ModelNotFoundError)."""
        return self._registry.get(ModelRef.parse(name))

    def categories(self) -> List[Category]:
        """Return all categories present in the catalog."""
        seen = []
        for spec in self._registry.list_all():
            if spec.category not in seen:
                seen.append(spec.category)
        return seen

    def recommend(self, task: str) -> List[ModelSpec]:
        """Recommend models for a task."""
        return self._registry.recommend(task)

    def list_all(self) -> List[ModelSpec]:
        """List every known model."""
        return self._registry.list_all()

    def by_category(self, category: Category) -> List[ModelSpec]:
        """List models in a category."""
        return self._registry.by_category(category)


__all__ = ["RegistryService"]
