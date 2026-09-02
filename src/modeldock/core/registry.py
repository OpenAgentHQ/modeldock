"""RegistryService — discovery over a RegistryPort.

Implements search/info/categories/recommend by composing the registry adapter.
See Architecture.md §9.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from modeldock.domain.model import Category, ModelInfo, ModelRef, ModelSpec
from modeldock.ports.registry import RegistryPort

# Relative weights for the three match tiers described in the issue:
# name > capability > description. Sub-tiers (exact vs. startswith vs.
# substring) exist within "name" so an exact name match always wins.
_NAME_EXACT_SCORE = 100.0
_NAME_PREFIX_SCORE = 60.0
_NAME_SUBSTRING_SCORE = 30.0
_ALIAS_EXACT_SCORE = 45.0
_ALIAS_SUBSTRING_SCORE = 20.0
_CAPABILITY_EXACT_SCORE = 20.0
_CAPABILITY_SUBSTRING_SCORE = 10.0
_CATEGORY_MATCH_SCORE = 8.0
_DESCRIPTION_SUBSTRING_SCORE = 3.0


@dataclass(frozen=True)
class ScoredModelSpec:
    """A ``ModelSpec`` paired with its relevance score for a search query.

    Higher scores are more relevant. ``score`` is not normalized to any
    fixed range; it is only meaningful for ordering results of the same
    query against each other.
    """

    spec: ModelSpec
    score: float


def _as_lower_list(value: object) -> List[str]:
    """Best-effort coercion of a spec field into a lowercased string list.

    Registry/domain fields for capabilities/aliases are expected to be
    iterables of strings, but we defend against ``None`` or a bare string
    so a slightly-off schema doesn't blow up search entirely.
    """
    if not value:
        return []
    if isinstance(value, str):
        return [value.lower()]
    return [str(item).lower() for item in value]


def _score_spec(spec: ModelSpec, query: str) -> float:
    """Score how relevant ``spec`` is to ``query``.

    Ranking order (per issue #79): name > capability > description.
    Within "name", exact match > prefix match > substring match. Category
    and alias matches are treated as name-adjacent signals but weighted
    below a direct name hit.
    """
    name = str(getattr(spec, "name", "")).lower()
    aliases = _as_lower_list(getattr(spec, "aliases", None))
    capabilities = _as_lower_list(getattr(spec, "capabilities", None))
    category = getattr(spec, "category", None)
    category_str = str(category).lower() if category is not None else ""
    description = str(getattr(spec, "description", "") or "").lower()

    score = 0.0

    # --- Name (highest tier) ---
    if name == query:
        score += _NAME_EXACT_SCORE
    elif name.startswith(query):
        score += _NAME_PREFIX_SCORE
    elif query in name:
        score += _NAME_SUBSTRING_SCORE
    elif query in aliases:
        score += _ALIAS_EXACT_SCORE
    elif any(query in alias for alias in aliases):
        score += _ALIAS_SUBSTRING_SCORE

    # --- Capability (middle tier) ---
    if query in capabilities:
        score += _CAPABILITY_EXACT_SCORE
    elif any(query in cap for cap in capabilities):
        score += _CAPABILITY_SUBSTRING_SCORE

    if category_str and (query == category_str or query in category_str):
        score += _CATEGORY_MATCH_SCORE

    # --- Description (lowest tier) ---
    if query and query in description:
        score += _DESCRIPTION_SUBSTRING_SCORE

    return score


class RegistryService:
    """Application service for model discovery."""

    def __init__(self, registry: RegistryPort) -> None:
        self._registry = registry

    def search(self, query: str) -> List[ScoredModelSpec]:
        """Search the catalog by name/alias/capability/category/description.

        Results are ranked by relevance — name matches outrank capability
        matches, which outrank description-only matches — and returned
        with their scores, highest first. Ties are broken alphabetically
        by model name for stable, predictable output.

        Returns an empty list for a blank/whitespace-only query.
        """
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        candidates = self._registry.list_all()
        scored = (
            ScoredModelSpec(spec=spec, score=_score_spec(spec, normalized_query))
            for spec in candidates
        )
        relevant = [result for result in scored if result.score > 0]
        relevant.sort(
            key=lambda result: (-result.score, str(getattr(result.spec, "name", "")))
        )
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


__all__ = ["RegistryService", "ScoredModelSpec"]
