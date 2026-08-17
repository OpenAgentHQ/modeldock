"""Tests for HuggingFaceCatalogProvider — live GGUF catalog via the Hub API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from modeldock.adapters.registry.huggingface_catalog import (
    HuggingFaceCatalogProvider,
    _detect_capabilities,
    _detect_category,
)
from modeldock.common.errors import ModelNotFoundError
from modeldock.domain.model import Capability, Category, ModelRef, RuntimeBackend

# ---------------------------------------------------------------------------
# Sample Hub API payload for testing
# ---------------------------------------------------------------------------

SAMPLE_PAYLOAD: List[Dict[str, Any]] = [
    {
        "id": "lmstudio-community/Qwen2.5-Coder-7B-Instruct-GGUF",
        "pipeline_tag": "text-generation",
        "tags": ["gguf", "conversational", "text-generation"],
    },
    {
        "id": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "pipeline_tag": "feature-extraction",
        "tags": ["gguf", "feature-extraction"],
    },
    {
        "id": "lmstudio-community/Qwen2-VL-7B-Instruct-GGUF",
        "pipeline_tag": "image-text-to-text",
        "tags": ["gguf", "image-text-to-text", "conversational"],
    },
    {
        "id": "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
        "pipeline_tag": "text-generation",
        "tags": ["gguf", "conversational", "text-generation", "function-calling"],
    },
    # No "id" — must be skipped rather than raising.
    {"pipeline_tag": "text-generation", "tags": []},
]


def _patched_client(payload: List[Dict[str, Any]] | None = None, raises: bool = False) -> Any:
    """Build a mock create_client() context manager returning ``payload``."""
    mock_client = MagicMock()
    if raises:
        mock_client.get.side_effect = Exception("network unavailable")
    else:
        mock_response = MagicMock()
        mock_response.json.return_value = payload if payload is not None else SAMPLE_PAYLOAD
        mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# Auto-detection tests
# ---------------------------------------------------------------------------


class TestDetectCategory:
    def test_embedding_by_name(self) -> None:
        assert _detect_category("nomic-ai/nomic-embed-text-v1.5-GGUF", None, []) == (
            Category.EMBEDDING
        )

    def test_embedding_by_pipeline_tag(self) -> None:
        assert _detect_category("some/repo-GGUF", "feature-extraction", []) == Category.EMBEDDING

    def test_coding_by_name(self) -> None:
        assert _detect_category("lmstudio-community/Qwen2.5-Coder-7B-GGUF", None, []) == (
            Category.CODING
        )

    def test_vision_by_pipeline_tag(self) -> None:
        assert _detect_category("some/repo-GGUF", "image-text-to-text", []) == Category.VISION

    def test_instruct_by_name(self) -> None:
        assert _detect_category("meta/Llama-3.1-8B-Instruct-GGUF", "text-generation", []) == (
            Category.INSTRUCT
        )

    def test_unknown_defaults_to_chat(self) -> None:
        assert _detect_category("some/random-repo", None, []) == Category.CHAT


class TestDetectCapabilities:
    def test_embedding_pipeline_tag_only_embed(self) -> None:
        caps = _detect_capabilities("feature-extraction", ["gguf"])
        assert caps == [Capability.EMBED]

    def test_chat_defaults(self) -> None:
        caps = _detect_capabilities("text-generation", ["gguf", "conversational"])
        assert Capability.CHAT in caps
        assert Capability.COMPLETION in caps
        assert Capability.EMBED not in caps

    def test_vision_capability(self) -> None:
        caps = _detect_capabilities("image-text-to-text", ["gguf"])
        assert Capability.VISION in caps

    def test_tool_use_from_tags(self) -> None:
        caps = _detect_capabilities("text-generation", ["gguf", "function-calling"])
        assert Capability.TOOL_USE in caps


# ---------------------------------------------------------------------------
# HuggingFaceCatalogProvider tests (mocked network)
# ---------------------------------------------------------------------------


class TestHuggingFaceCatalogProvider:
    def test_rejects_unsupported_backend(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.OLLAMA)

    def test_loads_from_network(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

            specs = registry.list_all()
            # The entry with no "id" is skipped.
            assert len(specs) == len(SAMPLE_PAYLOAD) - 1
            names = [s.name for s in specs]
            assert "lmstudio-community/Qwen2.5-Coder-7B-Instruct-GGUF" in names

    def test_specs_tagged_with_constructing_backend(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LLAMACPP)

            spec = registry.get(ModelRef.parse("lmstudio-community/Qwen2.5-Coder-7B-Instruct-GGUF"))
            assert spec.backend_hints == [RuntimeBackend.LLAMACPP]

    def test_falls_back_to_cache_when_offline(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client(raises=True)
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

            assert len(registry.list_all()) == len(SAMPLE_PAYLOAD) - 1

    def test_empty_when_no_network_and_no_cache(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client(raises=True)
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

            assert registry.list_all() == []

    def test_get_unknown_raises(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

            with pytest.raises(ModelNotFoundError):
                registry.get(ModelRef.parse("nonexistent/repo"))

    def test_models_for_category_maps_to_backend_refs(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

            refs = registry.models_for_category(Category.CODING)
            assert refs
            assert all(r.backend is RuntimeBackend.LM_STUDIO for r in refs)
            assert any("Qwen2.5-Coder" in r.name for r in refs)

    def test_models_for_capability_maps_to_backend_refs(self, tmp_path: Path) -> None:
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LLAMACPP)

            refs = registry.models_for_capability(Capability.EMBED)
            assert refs
            assert all(r.backend is RuntimeBackend.LLAMACPP for r in refs)

    def test_shares_one_cache_file_across_backends(self, tmp_path: Path) -> None:
        """LM Studio and llama.cpp both consume GGUF, so one fetch serves both."""
        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client()
            HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LM_STUDIO)

        assert (tmp_path / "huggingface_gguf_catalog.json").exists()

        with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
            mock_factory.return_value = _patched_client(raises=True)
            registry = HuggingFaceCatalogProvider(tmp_path, RuntimeBackend.LLAMACPP)

            # Served from the LM Studio fetch's cache despite no network here.
            assert registry.list_all()
