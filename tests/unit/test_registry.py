"""Unit tests for RegistryService and BundledRegistry."""

from __future__ import annotations

import pytest

from modeldock.adapters.registry import BundledRegistry
from modeldock.common.errors import ModelNotFoundError
from modeldock.core.registry import RegistryService
from modeldock.domain.model import Category, ModelRef


def test_registry_service_search_delegates(fake_registry: object) -> None:
    svc = RegistryService(fake_registry)
    assert svc.search("llama")


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


def test_bundled_registry_loads_catalog() -> None:
    reg = BundledRegistry()
    specs = reg.list_all()
    assert len(specs) >= 1
    names = {s.name for s in specs}
    assert "llama3" in names


def test_bundled_registry_get_by_alias() -> None:
    reg = BundledRegistry()
    spec = reg.get(ModelRef.parse("llama3"))
    assert spec.name == "llama3"


def test_bundled_registry_unknown_raises() -> None:
    reg = BundledRegistry()
    with pytest.raises(ModelNotFoundError):
        reg.get(ModelRef.parse("ghost-model"))


def test_bundled_registry_search_case_insensitive() -> None:
    reg = BundledRegistry()
    # "META" should match the llama3 description "Meta ..."
    hits = reg.search("META")
    assert any(s.name == "llama3" for s in hits)


def test_bundled_registry_recommend_capability() -> None:
    reg = BundledRegistry()
    hits = reg.recommend("coding")
    assert hits  # at least one coding model in the bundled catalog


def test_bundled_registry_by_category() -> None:
    reg = BundledRegistry()
    chat = reg.by_category(Category.CHAT)
    assert chat
