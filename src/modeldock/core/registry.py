"""RegistryService — discovery over a RegistryPort.

Implements search/info/categories/recommend by composing the registry adapter.
See Architecture.md §9.
"""

from __future__ import annotations

from typing import List

from modeldock.domain.model import Category, ModelInfo, ModelRef, ModelSpec
from modeldock.ports.registry import RegistryPort


class RegistryService:
    """Application service for model discovery."""

    def __init__(self, registry: RegistryPort) -> None:
        self._registry = registry

    def search(
        self, 
        query: str = "", 
        category: str | None = None, 
        capability: str | None = None, 
        min_ram: int | None = None
    ) -> List[ModelSpec]:
        """Search the catalog by name/alias/capability/category."""
        # 1. Base search: use query if provided, otherwise grab all to filter
        if query:
            results = self._registry.search(query)
        else:
            results = self._registry.list_all()

        # 2. Apply filters safely 
        if category is not None:
            results = [
                m for m in results 
                if m.category == category or (hasattr(m.category, 'value') and m.category.value == category)
            ]
            
        if capability is not None:
            results = [
                m for m in results 
                if capability in getattr(m, 'capabilities', [])
            ]
            
        if min_ram is not None:
            results = [
                m for m in results 
                if getattr(m, 'ram', 0) >= min_ram
            ]

        return results

    def info(self, name: str, installed_tags: List[str] | None = None) -> ModelInfo:
        """Return metadata for a model, enriched with installed tags.

        ``installed_tags`` are the concrete tags present in the active runtime
        (e.g. ``["8b", "latest"]``). When omitted, only catalog metadata is
        returned and ``installed`` is ``False``. Raises ``ModelNotFoundError``
        when the model is unknown to the registry.
        """
        spec = self._registry.get(ModelRef.parse(name))
        return ModelInfo.from_spec(spec, installed_tags or [])

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