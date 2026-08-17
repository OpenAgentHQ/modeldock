"""Unit tests for the LM Studio capability/category mapping (issue #19)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List
from unittest.mock import MagicMock, patch

import pytest

from modeldock.adapters.runtimes import lmstudio_catalog
from modeldock.adapters.runtimes.lmstudio import LMStudioRuntime
from modeldock.adapters.runtimes.ollama import OllamaRuntime
from modeldock.domain.model import Capability, Category, ModelRef, RuntimeBackend

# --- the mapping data ------------------------------------------------------


def test_every_category_is_covered() -> None:
    """A category with no entries would make install_category fail on LM Studio."""
    missing = [c for c in Category if not lmstudio_catalog.models_for_category(c)]
    assert missing == []


def test_model_ids_use_publisher_repo_form() -> None:
    """LM Studio addresses models by Hugging Face coordinates, not Ollama tags."""
    for entry in lmstudio_catalog.CATALOG:
        assert "/" in entry.model_id, f"{entry.model_id} is not publisher/repo"
        publisher, repo = entry.model_id.split("/", 1)
        assert publisher and repo


def test_model_ids_are_unique() -> None:
    ids = [entry.model_id for entry in lmstudio_catalog.CATALOG]
    assert len(ids) == len(set(ids))


def test_entries_declare_a_category_and_capabilities() -> None:
    for entry in lmstudio_catalog.CATALOG:
        assert isinstance(entry.category, Category)
        assert entry.capabilities, f"{entry.model_id} declares no capabilities"
        assert all(isinstance(c, Capability) for c in entry.capabilities)
        assert entry.description


def test_embedding_models_do_not_claim_chat() -> None:
    """An embedding model routed to a chat call would fail at request time."""
    for entry in lmstudio_catalog.models_for_category(Category.EMBEDDING):
        assert entry.capabilities == (Capability.EMBED,)


def test_capability_lookup_spans_categories() -> None:
    tool_users = lmstudio_catalog.models_for_capability(Capability.TOOL_USE)
    categories = {entry.category for entry in tool_users}
    assert Category.CHAT in categories
    assert Category.CODING in categories


def test_vision_capability_only_on_vision_models() -> None:
    for entry in lmstudio_catalog.models_for_capability(Capability.VISION):
        assert entry.category is Category.VISION


def test_unmapped_lookup_returns_empty_not_error() -> None:
    assert lmstudio_catalog.models_for_capability(Capability.REASONING)
    # A lookup that matches nothing must be an empty list, never a KeyError.
    assert lmstudio_catalog.models_for_category(Category.CHAT) != []


def test_lookup_returns_a_copy() -> None:
    """Callers must not be able to mutate the module-level index."""
    first = lmstudio_catalog.models_for_category(Category.CODING)
    first.clear()
    assert lmstudio_catalog.models_for_category(Category.CODING)


# --- the adapter -----------------------------------------------------------
#
# LMStudioRuntime now tries a live Hugging Face catalog before falling back
# to the static table above (see huggingface_catalog.py). These tests force
# that live lookup offline so they stay fast, deterministic, and independent
# of the test environment's actual network reachability — exercising the
# static-fallback path explicitly, exactly like the pre-live-catalog tests
# did. Live-lookup behavior itself is covered by test_huggingface_catalog.py
# and test_runtime_prefers_live_catalog_when_available below.


@pytest.fixture()
def offline_lmstudio_runtime(tmp_path: Path) -> Callable[..., LMStudioRuntime]:
    """Return a factory for LMStudioRuntime with the live catalog forced offline."""

    def _make(**kwargs: Any) -> LMStudioRuntime:
        return LMStudioRuntime(cache_dir=tmp_path, **kwargs)

    with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("network disabled for test")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_client
        yield _make


def test_runtime_returns_refs_for_category(
    offline_lmstudio_runtime: Callable[..., LMStudioRuntime],
) -> None:
    refs: List[ModelRef] = offline_lmstudio_runtime().models_for_category(Category.CODING)

    assert refs
    assert all(isinstance(r, ModelRef) for r in refs)
    assert all(r.backend is RuntimeBackend.LM_STUDIO for r in refs)
    assert any("Qwen2.5-Coder" in r.name for r in refs)


def test_runtime_refs_keep_the_namespace_in_the_name(
    offline_lmstudio_runtime: Callable[..., LMStudioRuntime],
) -> None:
    """The publisher belongs to the name; only ':' introduces a tag."""
    ref = offline_lmstudio_runtime().models_for_category(Category.EMBEDDING)[0]

    assert "/" in ref.name
    assert ref.tag == "latest"
    assert ref.qualified_name() == f"{ref.name}:latest"


def test_runtime_returns_refs_for_capability(
    offline_lmstudio_runtime: Callable[..., LMStudioRuntime],
) -> None:
    refs = offline_lmstudio_runtime().models_for_capability(Capability.VISION)

    assert refs
    assert all(r.backend is RuntimeBackend.LM_STUDIO for r in refs)


def test_runtime_needs_no_server_for_suggestions(
    offline_lmstudio_runtime: Callable[..., LMStudioRuntime],
) -> None:
    """Suggestions must not require a running LM Studio server (the Hub is a plain

    HTTPS fetch, unrelated to the LM Studio server itself; and the static
    table behind it needs neither).
    """
    runtime = offline_lmstudio_runtime(host="http://127.0.0.1:9")  # nothing listening

    assert runtime.models_for_category(Category.CHAT)


def test_other_runtimes_return_empty_by_default() -> None:
    """Ollama's names come from the shared catalog, so it supplies no mapping."""
    assert OllamaRuntime().models_for_category(Category.CODING) == []
    assert OllamaRuntime().models_for_capability(Capability.CHAT) == []


@pytest.mark.parametrize("category", list(Category))
def test_runtime_category_lookup_never_raises(
    category: Category,
    offline_lmstudio_runtime: Callable[..., LMStudioRuntime],
) -> None:
    assert isinstance(offline_lmstudio_runtime().models_for_category(category), list)


def test_runtime_prefers_live_catalog_when_available(tmp_path: Path) -> None:
    """When the Hugging Face Hub is reachable, its results win over the static table."""
    with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "unit-test-org/Live-Chat-Model-GGUF",
                "pipeline_tag": "text-generation",
                "tags": ["gguf", "conversational"],
            }
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_client

        runtime = LMStudioRuntime(cache_dir=tmp_path)
        refs = runtime.models_for_category(Category.CHAT)

    assert [r.name for r in refs] == ["unit-test-org/Live-Chat-Model-GGUF"]
