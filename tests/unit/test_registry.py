"""Unit tests for RegistryService and BundledRegistry."""
from __future__ import annotations

from typing import List

import pytest

from modeldock.adapters.registry import BundledRegistry
from modeldock.common.errors import ModelNotFoundError
from modeldock.core.registry import RegistryService
from modeldock.domain.model import Capability, Category, ModelRef, ModelSpec


class _StaticRegistry:
    """A minimal RegistryPort stand-in with a fixed, known catalog.

    Used for ranking-specific tests so assertions don't depend on whatever
    the shared ``fake_registry`` fixture happens to contain.
    """

    def __init__(self, specs: List[ModelSpec]) -> None:
        self._specs = specs

    def list_all(self) -> List[ModelSpec]:
        return list(self._specs)

    def get(self, ref: ModelRef) -> ModelSpec:
        for spec in self._specs:
            if spec.name == ref.name:
                return spec
        raise ModelNotFoundError(f"Unknown model: {ref.name}")

    def search(self, query: str) -> List[ModelSpec]:
        # Intentionally naive/unranked — RegistryService.search must rank via
        # list_all() + domain scoring, not depend on this method at all.
        q = query.lower()
        return [s for s in self._specs if q in s.name.lower()]

    def recommend(self, task: str) -> List[ModelSpec]:
        return []

    def by_category(self, category: Category) -> List[ModelSpec]:
        return [s for s in self._specs if s.category == category]


@pytest.fixture()
def ranking_registry() -> _StaticRegistry:
    return _StaticRegistry(
        [
            ModelSpec(
                name="llama3",
                aliases=["llama"],
                category=Category.CHAT,
                capabilities=[Capability.CHAT],
                description="Meta's Llama 3 chat model.",
            ),
            ModelSpec(
                name="qwen3",
                aliases=[],
                category=Category.CODING,
                capabilities=[Capability.CHAT, Capability.TOOL_USE],
                description="A coding-focused model, plays well with llama-style prompts.",
            ),
            ModelSpec(
                name="minilm",
                aliases=[],
                category=Category.EMBEDDING,
                capabilities=[Capability.EMBED],
                description="Small embedding model, unrelated to chat models.",
            ),
        ]
    )


def test_registry_service_search_delegates(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    assert svc.search("llama")


def test_registry_service_search_returns_scored_results(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    results = svc.search("llama")
    assert results
    for result in results:
        assert hasattr(result, "spec")
        assert hasattr(result, "score")
        assert result.score > 0


def test_registry_service_search_ranks_exact_name_match_first(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    results = svc.search("llama3")
    assert results[0].spec.name == "llama3"
    # An exact name match should score strictly higher than a mention
    # buried in another model's description.
    assert results[0].score > results[-1].score


def test_registry_service_search_ranks_capability_over_description(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    results = svc.search("chat")
    order = [r.spec.name for r in results]
    # "llama3"/"qwen3" declare the "chat" capability directly; "minilm"
    # only mentions "chat models" in its description. Capability should
    # outrank a description-only mention.
    assert order.index("llama3") < order.index("minilm")
    assert order.index("qwen3") < order.index("minilm")


def test_registry_service_search_is_case_insensitive(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    assert svc.search("LLAMA3")[0].spec.name == "llama3"


def test_registry_service_search_empty_query_returns_empty(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    assert svc.search("") == []
    assert svc.search("   ") == []


def test_registry_service_search_no_match_returns_empty(
    ranking_registry: _StaticRegistry,
) -> None:
    svc = RegistryService(ranking_registry)
    assert svc.search("totally-unrelated-xyz") == []


def test_registry_service_info_resolves(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    spec = svc.info("llama3")
    assert spec.name == "llama3"


def test_registry_service_info_unknown_raises(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    with pytest.raises(ModelNotFoundError):
        svc.info("nope")


def test_registry_service_categories(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    assert Category.CHAT in svc.categories()


def test_registry_service_by_category(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    assert svc.by_category(Category.CHAT)


# BundledRegistry tests — skipped when catalog.json is not present (deleted in v0.1.3)
_SKIP_REASON = "catalog.json not present (deleted in v0.1.3)"


def _catalog_json_exists() -> bool:
    from pathlib import Path

    catalog_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "modeldock"
        / "data"
        / "catalog.json"
    )
    return catalog_path.exists()


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_loads_catalog() -> None:
    reg = BundledRegistry()
    specs = reg.list_all()
    assert len(specs) >= 1
    names = {s.name for s in specs}
    assert "llama3" in names


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_get_by_alias() -> None:
    reg = BundledRegistry()
    spec = reg.get(ModelRef.parse("llama3"))
    assert spec.name == "llama3"


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_unknown_raises() -> None:
    reg = BundledRegistry()
    with pytest.raises(ModelNotFoundError):
        reg.get(ModelRef.parse("ghost-model"))


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_search_case_insensitive() -> None:
    reg = BundledRegistry()
    # "META" should match the llama3 description "Meta ..."
    hits = reg.search("META")
    assert any(s.name == "llama3" for s in hits)


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_recommend_capability() -> None:
    reg = BundledRegistry()
    hits = reg.recommend("coding")
    assert hits  # at least one coding model in the bundled catalog


@pytest.mark.skipif(not _catalog_json_exists(), reason=_SKIP_REASON)
def test_bundled_registry_by_category() -> None:
    reg = BundledRegistry()
    chat = reg.by_category(Category.CHAT)
    assert chat
