"""Tests for OllamaLibraryRegistry — dynamic catalog from ollama.com."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modeldock.adapters.registry.ollama_library import (
    OllamaLibraryRegistry,
    _detect_capabilities,
    _detect_category,
    _load_cache,
    _save_cache,
    _scrape_library_html,
)
from modeldock.common.errors import ModelNotFoundError
from modeldock.domain.model import Capability, Category, ModelRef

# ---------------------------------------------------------------------------
# Sample HTML for testing
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html>
<body>
<div class="models">
  <a href="/library/llama3">
    <h2>llama3</h2>
    <p>Meta Llama 3 instruction-tuned chat model.</p>
    <span class="tag">tools</span>
    <span class="tag">8b</span>
    <span class="tag">70b</span>
  </a>
  <a href="/library/codellama">
    <h2>codellama</h2>
    <p>Code-specialized Llama for coding tasks.</p>
    <span class="tag">tools</span>
    <span class="tag">7b</span>
    <span class="tag">13b</span>
  </a>
  <a href="/library/llava">
    <h2>llava</h2>
    <p>Visual language model for image understanding.</p>
    <span class="tag">vision</span>
    <span class="tag">7b</span>
  </a>
  <a href="/library/nomic-embed-text">
    <h2>nomic-embed-text</h2>
    <p>Mistral Nomic Embed text model.</p>
    <span class="tag">embedding</span>
  </a>
  <a href="/library/deepseek-r1">
    <h2>deepseek-r1</h2>
    <p>DeepSeek R1 reasoning model.</p>
    <span class="tag">thinking</span>
    <span class="tag">tools</span>
  </a>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Auto-detection tests
# ---------------------------------------------------------------------------


class TestDetectCategory:
    def test_embedding_model(self) -> None:
        assert _detect_category("nomic-embed-text", ["embedding"]) == Category.EMBEDDING

    def test_coding_model(self) -> None:
        assert _detect_category("codellama", ["tools"]) == Category.CODING

    def test_vision_model_by_name(self) -> None:
        assert _detect_category("llava", []) == Category.VISION

    def test_vision_model_by_html_tag(self) -> None:
        assert _detect_category("moondream", ["vision"]) == Category.VISION

    def test_reasoning_model(self) -> None:
        assert _detect_category("deepseek-r1", ["thinking"]) == Category.REASONING

    def test_chat_model_default(self) -> None:
        assert _detect_category("llama3", ["tools"]) == Category.CHAT

    def test_unknown_model_defaults_to_chat(self) -> None:
        assert _detect_category("some-random-model", []) == Category.CHAT


class TestDetectCapabilities:
    def test_tools_capability(self) -> None:
        caps = _detect_capabilities("llama3", ["tools"])
        assert Capability.TOOL_USE in caps
        assert Capability.CHAT in caps
        assert Capability.COMPLETION in caps

    def test_vision_capability(self) -> None:
        caps = _detect_capabilities("llava", ["vision"])
        assert Capability.VISION in caps
        assert Capability.CHAT in caps

    def test_thinking_capability(self) -> None:
        caps = _detect_capabilities("deepseek-r1", ["thinking"])
        assert Capability.REASONING in caps

    def test_embedding_model(self) -> None:
        caps = _detect_capabilities("nomic-embed-text", ["embedding"])
        assert Capability.EMBED in caps
        assert Capability.CHAT not in caps
        assert Capability.COMPLETION not in caps

    def test_no_html_tags_defaults(self) -> None:
        caps = _detect_capabilities("llama3", [])
        assert Capability.CHAT in caps
        assert Capability.COMPLETION in caps


# ---------------------------------------------------------------------------
# HTML scraping tests
# ---------------------------------------------------------------------------


class TestScrapeLibraryHtml:
    def test_extracts_model_names(self) -> None:
        models = _scrape_library_html(SAMPLE_HTML)
        names = [m["name"] for m in models]
        assert "llama3" in names
        assert "codellama" in names
        assert "llava" in names
        assert "nomic-embed-text" in names
        assert "deepseek-r1" in names

    def test_extracts_descriptions(self) -> None:
        models = _scrape_library_html(SAMPLE_HTML)
        llama = next(m for m in models if m["name"] == "llama3")
        assert "Meta Llama 3" in llama["description"]

    def test_extracts_capability_tags(self) -> None:
        models = _scrape_library_html(SAMPLE_HTML)
        llama = next(m for m in models if m["name"] == "llama3")
        assert "tools" in llama["capability_tags"]

    def test_deduplicates_models(self) -> None:
        # HTML with duplicate links
        html = """
        <a href="/library/llama3"><h2>llama3</h2><p>Test</p></a>
        <a href="/library/llama3"><h2>llama3</h2><p>Test</p></a>
        """
        models = _scrape_library_html(html)
        names = [m["name"] for m in models]
        assert names.count("llama3") == 1

    def test_empty_html(self) -> None:
        models = _scrape_library_html("")
        assert models == []


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestCache:
    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "catalog_cache.json"
        models = [{"name": "llama3", "description": "Test", "capability_tags": ["tools"]}]
        _save_cache(cache_path, models)
        loaded = _load_cache(cache_path)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["name"] == "llama3"

    def test_expired_cache_returns_none(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "catalog_cache.json"
        data = {
            "version": 1,
            "scraped_at": time.time() - 100000,  # Expired
            "models": [{"name": "llama3"}],
        }
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        assert _load_cache(cache_path) is None

    def test_fresh_cache_returns_data(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "catalog_cache.json"
        data = {
            "version": 1,
            "scraped_at": time.time(),  # Fresh
            "models": [{"name": "llama3"}],
        }
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        loaded = _load_cache(cache_path)
        assert loaded is not None
        assert len(loaded) == 1

    def test_corrupt_cache_returns_none(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "catalog_cache.json"
        cache_path.write_text("not json", encoding="utf-8")
        assert _load_cache(cache_path) is None

    def test_missing_cache_returns_none(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "catalog_cache.json"
        assert _load_cache(cache_path) is None


# ---------------------------------------------------------------------------
# OllamaLibraryRegistry tests (with mocked network)
# ---------------------------------------------------------------------------


class TestOllamaLibraryRegistry:
    def test_loads_from_network(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            specs = registry.list_all()
            assert len(specs) >= 5
            names = [s.name for s in specs]
            assert "llama3" in names
            assert "codellama" in names

    def test_loads_from_cache_when_offline(self, tmp_path: Path) -> None:
        # Pre-populate cache
        cache_path = tmp_path / "catalog_cache.json"
        models = [
            {"name": "llama3", "description": "Test model", "capability_tags": ["tools"]},
            {"name": "codellama", "description": "Code model", "capability_tags": ["tools"]},
        ]
        _save_cache(cache_path, models)

        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Network unavailable")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            specs = registry.list_all()
            assert len(specs) == 2
            names = [s.name for s in specs]
            assert "llama3" in names

    def test_empty_when_no_network_and_no_cache(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Network unavailable")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            specs = registry.list_all()
            assert len(specs) == 0

    def test_search(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            results = registry.search("llama")
            assert len(results) >= 1
            assert any("llama" in s.name.lower() for s in results)

    def test_get_model(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            spec = registry.get(ModelRef.parse("llama3"))
            assert spec.name == "llama3"
            assert spec.category == Category.CHAT

    def test_get_unknown_raises(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            with pytest.raises(ModelNotFoundError):
                registry.get(ModelRef.parse("nonexistent-model"))

    def test_by_category(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            chat_models = registry.by_category(Category.CHAT)
            assert len(chat_models) >= 1

    def test_recommend(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            results = registry.recommend("coding")
            assert len(results) >= 1

    def test_auto_detected_category(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            registry = OllamaLibraryRegistry(cache_dir=tmp_path)

            # codellama should be detected as CODING
            codellama = registry.get(ModelRef.parse("codellama"))
            assert codellama.category == Category.CODING

            # llava should be detected as VISION
            llava = registry.get(ModelRef.parse("llava"))
            assert llava.category == Category.VISION

            # nomic-embed-text should be detected as EMBEDDING
            embed = registry.get(ModelRef.parse("nomic-embed-text"))
            assert embed.category == Category.EMBEDDING

    def test_caches_to_disk(self, tmp_path: Path) -> None:
        with patch(
            "modeldock.adapters.registry.ollama_library.create_client"
        ) as mock_client_factory:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = SAMPLE_HTML
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_factory.return_value = mock_client

            OllamaLibraryRegistry(cache_dir=tmp_path)

            cache_path = tmp_path / "catalog_cache.json"
            assert cache_path.exists()
