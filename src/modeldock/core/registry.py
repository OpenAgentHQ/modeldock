"""RegistryService — discovery over a RegistryPort.

Implements search/info/categories/recommend by composing the registry adapter.
See Architecture.md §9.
"""
from __future__ import annotations

from typing import List

from modeldock.domain.model import (
    Category,
    ModelAlias,
    ModelInfo,
    ModelRef,
    ModelSpec,
    ScoredModelSpec,
)
from modeldock.ports.registry import RegistryPort


class RegistryService:
    """Application service for model discovery."""

    def __init__(self, registry: RegistryPort) -> None:
        self._registry = registry

    def search(self, query: str) -> List[ScoredModelSpec]:
        """Search the catalog by name/alias/capability/category/description.

        Ranks results by relevance rather than delegating to the adapter's
        own ``search`` — name matches outrank capability matches, which
        outrank description-only matches (see issue #79 / ``ModelAlias.
        match_score``) — and returns each match paired with its score,
        highest first. Ties are broken alphabetically by model name for
        stable, predictable output. Returns ``[]`` for a blank query.
        """
        if not query or not query.strip():
            return []

        results = [
            ScoredModelSpec(spec=spec, score=ModelAlias.match_score(spec, query))
            for spec in self._registry.list_all()
        ]
        relevant = [result for result in results if result.score > 0]
        relevant.sort(key=lambda result: (-result.score, result.spec.name))
        return relevant

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
