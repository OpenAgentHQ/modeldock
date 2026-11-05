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
from modeldock.domain.source import BUNDLED, SourceInfo, SourceTrust

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


def load_bundled_catalog() -> List[Dict[str, Any]]:
    """Return the raw entries of the bundled catalog.json.

    Public counterpart to ``_load_catalog`` so other registries can read the
    shipped catalog without importing a private name.
    """
    return _load_catalog()


def catalog_entry_to_spec(raw: Dict[str, Any]) -> ModelSpec:
    """Coerce one raw catalog.json entry into a validated ``ModelSpec``.

    Shared by every registry that consumes catalog.json-shaped entries — the
    bundled catalog and any remote catalog served in the same format — so the
    enum coercion rules live in exactly one place instead of being reached for
    across class boundaries.
    """
    raw = dict(raw)
    raw["category"] = Category.from_value(raw["category"])
    raw["capabilities"] = [Capability.from_value(c) for c in raw.get("capabilities", [])]
    raw["backend_hints"] = [RuntimeBackend.from_value(b) for b in raw.get("backend_hints", [])]
    return ModelSpec.model_validate(raw)


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
            if spec.source is None:
                spec.source = BUNDLED
            self._specs[spec.name] = spec
            for alias in spec.aliases:
                self._by_alias[alias.lower()] = spec.name
            self._by_alias[spec.name.lower()] = spec.name

    @staticmethod
    def _to_spec(raw: Dict[str, Any]) -> ModelSpec:
        return catalog_entry_to_spec(raw)

    # --- RegistryPort -----------------------------------------------------

    def search(self, query: str) -> List[ModelSpec]:
        return [s for s in self._specs.values() if ModelAlias.matches_query(s, query)]

    def get(self, ref: ModelRef) -> ModelSpec:
        name = self._by_alias.get(ref.name.lower())
        if name is None:
            raise ModelNotFoundError(ref.name)
        return self._specs[name]

    def resolve(self, ref: ModelRef) -> ModelSpec:
        """Resolve a friendly/alias ``ref`` to its canonical spec."""
        return self.get(ref)

    def versions(self, ref: ModelRef) -> List[str]:
        """Return known version tags for ``ref`` (empty when unknown)."""
        try:
            return self.get(ref).version_tags()
        except ModelNotFoundError:
            return []

    def describe(self) -> List[SourceInfo]:
        """Describe the bundled fallback source (static, never primary)."""
        return [
            SourceInfo(
                name=BUNDLED,
                trust=SourceTrust.BUNDLED,
                live=False,
                backend=None,
                model_count=len(self._specs),
                cache_path=str(_catalog_path()),
                available=bool(self._specs),
            )
        ]

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


__all__ = ["BundledRegistry", "catalog_entry_to_spec", "load_bundled_catalog"]
