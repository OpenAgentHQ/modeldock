"""OllamaLibraryRegistry — dynamic catalog scraped from ollama.com/library.

Fetches the full model list from ollama.com, auto-detects categories and
capabilities from model names and HTML tags, and caches locally for offline
use. This is the default registry when ``catalog_source="auto"`` or
``catalog_source="ollama"``. Built on ``CachedCatalogRegistry``, the shared
fetch → cache → index pipeline every live catalog source uses. See
Architecture.md §9.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from modeldock.adapters.registry.base import CachedCatalogRegistry
from modeldock.common.catalog_cache import load_catalog_cache, save_catalog_cache
from modeldock.common.http import create_client
from modeldock.domain.model import (
    Capability,
    Category,
    ModelSpec,
    RuntimeBackend,
)

_LIBRARY_URL = "https://ollama.com/library"
_CACHE_FILENAME = "catalog_cache.json"
_CACHE_TTL_SECONDS = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

# Name patterns → Category (checked in order; first match wins)
_CATEGORY_PATTERNS: list[tuple[str, Category]] = [
    (r"embed", Category.EMBEDDING),
    (r"code", Category.CODING),
    (r"vision|llava|moondream|bakllava", Category.VISION),
    (r"r1|thinking|reason", Category.REASONING),
    (
        r"instruct|chat|gemma|llama|qwen|mistral|phi|deepseek|yi|command|"
        r"internlm|vicuna|openchat|neural|dolphin|falcon|starling|"
        r"openhermes|airobot|bagel|EXAONE|granite|smol|tulu|solar|kimi|minimax",
        Category.CHAT,
    ),
]

# HTML capability tags → Capability
_CAPABILITY_MAP: dict[str, Capability] = {
    "tools": Capability.TOOL_USE,
    "vision": Capability.VISION,
    "thinking": Capability.REASONING,
    "audio": Capability.CHAT,  # audio is a modality, map to CHAT for now
    "embedding": Capability.EMBED,
}


def _detect_category(name: str, html_caps: List[str]) -> Category:
    """Auto-detect category from model name and HTML capability tags."""
    name_lower = name.lower()

    # Check name patterns first
    for pattern, cat in _CATEGORY_PATTERNS:
        if re.search(pattern, name_lower):
            return cat

    # Check HTML capability tags
    if "embedding" in html_caps:
        return Category.EMBEDDING
    if "vision" in html_caps:
        return Category.VISION

    return Category.CHAT


def _detect_capabilities(name: str, html_caps: List[str]) -> List[Capability]:
    """Auto-detect capabilities from HTML tags and model name."""
    caps: list[Capability] = []

    # Map HTML tags to capabilities
    for tag in html_caps:
        tag_lower = tag.strip().lower()
        if tag_lower in _CAPABILITY_MAP:
            cap = _CAPABILITY_MAP[tag_lower]
            if cap not in caps:
                caps.append(cap)

    # Always include CHAT and COMPLETION for non-embedding models
    if "embedding" not in html_caps:
        if Capability.CHAT not in caps:
            caps.append(Capability.CHAT)
        if Capability.COMPLETION not in caps:
            caps.append(Capability.COMPLETION)

    return caps or [Capability.CHAT, Capability.COMPLETION]


# ---------------------------------------------------------------------------
# HTML scraping
# ---------------------------------------------------------------------------

# Patterns for extracting model data from ollama.com/library HTML
_MODEL_LINK_RE = re.compile(r'<a[^>]*href="/library/([^"]+)"[^>]*>', re.IGNORECASE)
_MODEL_DESC_RE = re.compile(r"<p[^>]*>([^<]+)</p>", re.IGNORECASE)
_CAPABILITY_PILL_RE = re.compile(
    r'<span[^>]*class="[^"]*tag[^"]*"[^>]*>([^<]+)</span>', re.IGNORECASE
)


def _scrape_library_html(html: str) -> List[Dict[str, Any]]:
    """Extract model entries from ollama.com/library HTML."""
    models: list[Dict[str, Any]] = []

    # Find all model links
    links = _MODEL_LINK_RE.findall(html)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_links: list[str] = []
    for link in links:
        # Strip any trailing path segments (e.g., "/library/llama3.1/tags")
        model_name = link.split("/")[0]
        if model_name not in seen:
            seen.add(model_name)
            unique_links.append(model_name)

    # For each model, try to find description and capabilities nearby
    for model_name in unique_links:
        # Find the section around this model link
        pattern = re.compile(
            rf'href="/library/{re.escape(model_name)}"(.*?)(?=href="/library/|$)',
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(html)
        section = match.group(1) if match else ""

        # Extract description
        desc_match = _MODEL_DESC_RE.search(section)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract capability pills
        caps = _CAPABILITY_PILL_RE.findall(section)
        # Filter out size tags (like "8b", "70b") - keep only capability tags
        capability_tags = [
            c.strip()
            for c in caps
            if c.strip().lower() not in ("latest",) and not re.match(r"^\d+[bB]$", c.strip())
        ]

        models.append(
            {
                "name": model_name,
                "description": description,
                "capability_tags": capability_tags,
            }
        )

    return models


# ---------------------------------------------------------------------------
# Cache management
#
# Thin wrappers around the shared TTL'd JSON cache (common/catalog_cache.py)
# so existing call sites/tests keep this module's own ``_save_cache`` /
# ``_load_cache`` names and signatures.
# ---------------------------------------------------------------------------


def _save_cache(cache_path: Path, models: List[Dict[str, Any]]) -> None:
    """Save scraped models to local cache."""
    save_catalog_cache(cache_path, models)


def _load_cache(cache_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Load models from local cache if fresh."""
    return load_catalog_cache(cache_path, _CACHE_TTL_SECONDS)


# ---------------------------------------------------------------------------
# Main registry
# ---------------------------------------------------------------------------


class OllamaLibraryRegistry(CachedCatalogRegistry):
    """Registry that scrapes ollama.com/library for the full model catalog.

    On initialization, fetches the model list from ollama.com, auto-detects
    categories and capabilities, and caches locally. Falls back to cache when
    offline. Implements ``RegistryPort`` via ``CachedCatalogRegistry``.
    """

    def __init__(self, cache_dir: Path) -> None:
        super().__init__(cache_dir, _CACHE_FILENAME, "registry.ollama_library")

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        return _load_cache(self._cache_path)

    def _fetch_from_network(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch model list from ollama.com/library."""
        try:
            with create_client(timeout=15.0) as client:
                resp = client.get(_LIBRARY_URL)
                resp.raise_for_status()
            models = _scrape_library_html(resp.text)
            if models:
                _save_cache(self._cache_path, models)
                self._logger.info("Scraped %d models from ollama.com", len(models))
            return models
        except Exception as exc:
            self._logger.debug("Network fetch failed: %s", exc)
            return None

    def _to_spec(self, raw: Dict[str, Any]) -> ModelSpec:
        """Convert scraped model dict to ModelSpec."""
        name = raw["name"]
        description = raw.get("description", "")
        html_caps = raw.get("capability_tags", [])

        category = _detect_category(name, html_caps)
        capabilities = _detect_capabilities(name, html_caps)

        return ModelSpec(
            name=name,
            aliases=[name],
            category=category,
            capabilities=capabilities,
            default_tag="latest",
            description=description,
            backend_hints=[RuntimeBackend.OLLAMA],
        )


__all__ = ["OllamaLibraryRegistry"]
