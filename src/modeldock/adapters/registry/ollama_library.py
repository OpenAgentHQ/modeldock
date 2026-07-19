"""OllamaLibraryRegistry — dynamic catalog scraped from ollama.com/library.

Fetches the full model list from ollama.com, auto-detects categories and
capabilities from model names and HTML tags, and caches locally for offline
use. This is the default registry when ``catalog_source="auto"`` or
``catalog_source="ollama"``. See Architecture.md §9.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from modeldock.common.errors import ModelNotFoundError
from modeldock.common.http import create_client
from modeldock.common.logging import get_logger
from modeldock.domain.model import (
    Capability,
    Category,
    ModelAlias,
    ModelRef,
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
_UNUSED_MODEL_NAME_RE = re.compile(r"<h2[^>]*>([^<]+)</h2>", re.IGNORECASE)
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
# ---------------------------------------------------------------------------


def _save_cache(cache_path: Path, models: List[Dict[str, Any]]) -> None:
    """Save scraped models to local cache."""
    data = {
        "version": 1,
        "scraped_at": time.time(),
        "models": models,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: write to temp file then replace
    tmp_path = cache_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(cache_path)
    except Exception:
        # Clean up on failure
        if tmp_path.exists():
            tmp_path.unlink()


def _load_cache(cache_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Load models from local cache if fresh."""
    if not cache_path.exists():
        return None
    try:
        raw: Dict[str, Any] = json.loads(cache_path.read_text(encoding="utf-8"))
        scraped_at = raw.get("scraped_at", 0)
        if time.time() - scraped_at > _CACHE_TTL_SECONDS:
            return None  # Cache expired
        models: List[Dict[str, Any]] = raw.get("models", [])
        return models
    except (json.JSONDecodeError, KeyError):
        return None


# ---------------------------------------------------------------------------
# Main registry
# ---------------------------------------------------------------------------


class OllamaLibraryRegistry:
    """Registry that scrapes ollama.com/library for the full model catalog.

    On initialization, fetches the model list from ollama.com, auto-detects
    categories and capabilities, and caches locally. Falls back to cache when
    offline. Implements ``RegistryPort``.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._logger = get_logger("registry.ollama_library")
        self._cache_path = cache_dir / _CACHE_FILENAME
        self._specs: Dict[str, ModelSpec] = {}
        self._by_alias: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Try network first, then cache, then raise."""
        models = self._fetch_from_network()
        if models is None:
            models = _load_cache(self._cache_path)
        if models is None:
            self._logger.warning(
                "No network and no cache; catalog will be empty. "
                "Run with network once to populate the cache."
            )
            return
        self._build_index(models)

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

    def _build_index(self, models: List[Dict[str, Any]]) -> None:
        """Build in-memory index from scraped model data."""
        for raw in models:
            spec = self._to_spec(raw)
            self._specs[spec.name] = spec
            for alias in spec.aliases:
                self._by_alias[alias.lower()] = spec.name
            self._by_alias[spec.name.lower()] = spec.name

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

    # --- RegistryPort -----------------------------------------------------

    def search(self, query: str) -> List[ModelSpec]:
        """Return specs whose name/alias/capability/category match ``query``."""
        return [s for s in self._specs.values() if ModelAlias.matches_query(s, query)]

    def get(self, ref: ModelRef) -> ModelSpec:
        """Return the canonical spec for ``ref`` (raises if unknown)."""
        name = self._by_alias.get(ref.name.lower())
        if name is None:
            raise ModelNotFoundError(ref.name)
        return self._specs[name]

    def by_category(self, category: Category) -> List[ModelSpec]:
        """Return all specs in a category."""
        return [s for s in self._specs.values() if s.category == category]

    def recommend(self, task: str) -> List[ModelSpec]:
        """Return specs recommended for a task (capability/category hint)."""
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
        """Return every known spec."""
        return list(self._specs.values())


__all__ = ["OllamaLibraryRegistry"]
