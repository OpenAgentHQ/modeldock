"""Unit tests for the domain layer (pure, no I/O)."""

from __future__ import annotations

import pytest

from modeldock.domain.errors import AliasResolutionError
from modeldock.domain.model import (
    Capability,
    Category,
    ModelAlias,
    ModelRef,
    ModelSpec,
    ModelVariant,
    RuntimeBackend,
)


def test_capability_from_value_case_insensitive() -> None:
    assert Capability.from_value("CHAT") == Capability.CHAT
    assert Capability.from_value("vision") == Capability.VISION


def test_capability_from_value_invalid() -> None:
    with pytest.raises(ValueError):
        Capability.from_value("telepathy")


def test_category_from_value() -> None:
    assert Category.from_value("coding") == Category.CODING
    with pytest.raises(ValueError):
        Category.from_value("nonsense")


def test_backend_from_value() -> None:
    assert RuntimeBackend.from_value("OLLAMA") == RuntimeBackend.OLLAMA
    assert RuntimeBackend.from_value("vllm") == RuntimeBackend.VLLM


def test_model_ref_parse_name_only() -> None:
    ref = ModelRef.parse("llama3")
    assert ref.name == "llama3"
    assert ref.tag == "latest"


def test_model_ref_parse_name_and_tag() -> None:
    ref = ModelRef.parse("llama3:8b")
    assert ref.name == "llama3"
    assert ref.tag == "8b"
    assert ref.qualified_name() == "llama3:8b"


def test_model_ref_parse_empty_raises() -> None:
    with pytest.raises(AliasResolutionError):
        ModelRef.parse("")


def test_model_ref_parse_invalid() -> None:
    with pytest.raises(AliasResolutionError):
        ModelRef.parse(":8b")


def test_model_spec_default_variant() -> None:
    spec = ModelSpec(
        name="x",
        category=Category.CHAT,
        variants=[ModelVariant(tag="8b"), ModelVariant(tag="70b")],
        default_tag="8b",
    )
    assert spec.default_variant().tag == "8b"


def test_model_spec_no_default_variant() -> None:
    spec = ModelSpec(name="x", category=Category.CHAT, default_tag="missing")
    assert spec.default_variant() is None


def test_alias_matches_query() -> None:
    spec = ModelSpec(
        name="llama3",
        aliases=["llama-3"],
        category=Category.CHAT,
        capabilities=[Capability.CHAT],
        description="Meta chat model",
    )
    assert ModelAlias.matches_query(spec, "llama")
    assert ModelAlias.matches_query(spec, "chat")
    assert ModelAlias.matches_query(spec, "meta")
    assert not ModelAlias.matches_query(spec, "vision")


def test_alias_resolve_success(fake_registry: object) -> None:
    spec = ModelAlias.resolve("llama3", fake_registry)
    assert spec.name == "llama3"


def test_alias_resolve_unknown_raises(fake_registry: object) -> None:
    with pytest.raises(AliasResolutionError):
        ModelAlias.resolve("does-not-exist", fake_registry)
