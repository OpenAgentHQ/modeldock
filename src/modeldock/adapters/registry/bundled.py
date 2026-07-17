"""BundledRegistry — reads the bundled catalog.json shipped with the package.

Works offline, zero-config. See Architecture.md §9. Catalog entries are
validated into ``ModelSpec`` via Pydantic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, cast

from modeldock.common.errors import ModelNotFoundError
from modeldock.common.logging import get_logger
from modeldock.domain.model import (
    Capability,
    Category,
    ModelAlias,
    ModelRef,
    ModelSpec,
    RuntimeBackend,
)

_CATALOG_FILENAME = "catalog.json"


def _catalog_path() -> Path:
    """Locate catalog.json relative to this package's data directory."""
    here = Path(__file__).resolve().parent
    candidate = here.parent.parent / "data" / _CATALOG_FILENAME
    return candidate


def _load_catalog() -> List[Dict[str, Any]]:
    path = _catalog_path()
    if not path.exists():
        raise ModelNotFoundError("catalog.json not found in package data")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return cast(List[Dict[str, Any]], data.get("models", []))


class BundledRegistry:
    """Registry backed by the bundled catalog.json."""

    def __init__(self) -> None:
        self._logger = get_logger("registry.bundled")
        self._specs: Dict[str, ModelSpec] = {}
        self._by_alias: Dict[str, str] = {}
        self._index()

    def _index(self) -> None:
        for raw in _load_catalog():
            spec = self._to_spec(raw)
            self._specs[spec.name] = spec
            for alias in spec.aliases:
                self._by_alias[alias.lower()] = spec.name
            self._by_alias[spec.name.lower()] = spec.name

    @staticmethod
    def _to_spec(raw: Dict[str, Any]) -> ModelSpec:
        raw = dict(raw)
        raw["category"] = Category.from_value(raw["category"])
        raw["capabilities"] = [Capability.from_value(c) for c in raw.get("capabilities", [])]
        raw["backend_hints"] = [RuntimeBackend.from_value(b) for b in raw.get("backend_hints", [])]
        return ModelSpec.model_validate(raw)

    # --- RegistryPort -----------------------------------------------------

    def search(self, query: str) -> List[ModelSpec]:
        return [s for s in self._specs.values() if ModelAlias.matches_query(s, query)]

    def get(self, ref: ModelRef) -> ModelSpec:
        name = self._by_alias.get(ref.name.lower())
        if name is None:
            raise ModelNotFoundError(ref.name)
        return self._specs[name]

    def by_category(self, category: Category) -> List[ModelSpec]:
        return [s for s in self._specs.values() if s.category == category]

    def recommend(self, task: str) -> List[ModelSpec]:
        q = (task or "").strip().lower()
        if not q:
            return list(self._specs.values())
        matched = [s for s in self._specs.values() if ModelAlias.matches_query(s, q)]
        if matched:
            return matched
        # Fall back to capability-based recommendation.
        try:
            cap = Capability.from_value(q)
            return [s for s in self._specs.values() if cap in s.capabilities]
        except ValueError:
            return []

    def list_all(self) -> List[ModelSpec]:
        return list(self._specs.values())


__all__ = ["BundledRegistry"]
