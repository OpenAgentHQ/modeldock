"""HuggingFaceCatalogProvider — live GGUF catalog via the Hugging Face Hub.

Neither LM Studio nor llama.cpp expose a searchable online catalog of their
own: both consume GGUF-format repositories directly from the Hugging Face
Hub. Previously LM Studio's category/capability suggestions came from a
hand-maintained static table (``adapters/runtimes/lmstudio_catalog.py``) and
llama.cpp had no catalog at all. This module queries the Hub's public
``/api/models`` endpoint (filtered to the ``gguf`` tag) so both runtimes can
discover models live instead.

Built on ``CachedCatalogRegistry``, so it gets the same fetch -> cache ->
index -> RegistryPort pipeline as ``OllamaLibraryRegistry`` for free — a new
live source only needed to implement fetching and parsing. See
Architecture.md §9.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from modeldock.adapters.registry.base import CachedCatalogRegistry
from modeldock.common.catalog_cache import load_catalog_cache, save_catalog_cache
from modeldock.common.http import create_client
from modeldock.domain.model import Capability, Category, ModelRef, ModelSpec, RuntimeBackend

_API_URL = "https://huggingface.co/api/models"
_CACHE_FILENAME = "huggingface_gguf_catalog.json"
_CACHE_TTL_SECONDS = 86400  # 24 hours, matches OllamaLibraryRegistry
_DEFAULT_LIMIT = 200

# Backends that consume GGUF directly and can use this provider.
SUPPORTED_BACKENDS = (RuntimeBackend.LM_STUDIO, RuntimeBackend.LLAMACPP)


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

# repo-id patterns -> Category (checked in order; first match wins)
_CATEGORY_PATTERNS: List[tuple[str, Category]] = [
    (r"embed|sentence-transformers", Category.EMBEDDING),
    (r"coder|code-|code_|codellama|starcoder", Category.CODING),
    (r"vision|vl-|-vl\b|llava|moondream|bakllava", Category.VISION),
    (r"r1-distill|reasoning|thinking|o1-|qwq", Category.REASONING),
    (r"instruct", Category.INSTRUCT),
]

_EMBEDDING_PIPELINE_TAGS = {"feature-extraction", "sentence-similarity"}
_VISION_PIPELINE_TAGS = {"image-text-to-text", "visual-question-answering"}
_TOOL_TAGS = {"function-calling", "tool-use"}


def _detect_category(repo_id: str, pipeline_tag: Optional[str], tags: List[str]) -> Category:
    """Auto-detect category from the repo id, pipeline tag, and Hub tags."""
    name_lower = repo_id.lower()
    for pattern, cat in _CATEGORY_PATTERNS:
        if re.search(pattern, name_lower):
            return cat

    pt = (pipeline_tag or "").lower()
    if pt in _EMBEDDING_PIPELINE_TAGS:
        return Category.EMBEDDING
    if pt in _VISION_PIPELINE_TAGS:
        return Category.VISION

    tag_set = {t.lower() for t in tags}
    if tag_set & _EMBEDDING_PIPELINE_TAGS:
        return Category.EMBEDDING
    if tag_set & _VISION_PIPELINE_TAGS:
        return Category.VISION

    return Category.CHAT


def _detect_capabilities(pipeline_tag: Optional[str], tags: List[str]) -> List[Capability]:
    """Auto-detect capabilities from the pipeline tag and Hub tags."""
    pt = (pipeline_tag or "").lower()
    tag_set = {t.lower() for t in tags}

    if pt in _EMBEDDING_PIPELINE_TAGS or tag_set & _EMBEDDING_PIPELINE_TAGS:
        return [Capability.EMBED]

    caps: List[Capability] = [Capability.CHAT, Capability.COMPLETION]
    if pt in _VISION_PIPELINE_TAGS or tag_set & _VISION_PIPELINE_TAGS:
        caps.append(Capability.VISION)
    if tag_set & _TOOL_TAGS:
        caps.append(Capability.TOOL_USE)
    return caps


# ---------------------------------------------------------------------------
# Main provider
# ---------------------------------------------------------------------------


class HuggingFaceCatalogProvider(CachedCatalogRegistry):
    """Registry that queries the Hugging Face Hub for GGUF-format models.

    One instance serves whichever ``backend`` it is constructed for (LM
    Studio or llama.cpp); both point at the same underlying GGUF universe and
    share one on-disk cache, so only one network fetch is needed regardless
    of how many GGUF-consuming runtimes are active.
    """

    def __init__(
        self,
        cache_dir: Path,
        backend: RuntimeBackend,
        limit: int = _DEFAULT_LIMIT,
    ) -> None:
        if backend not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"HuggingFaceCatalogProvider does not support backend {backend.value!r}"
            )
        self._backend = backend
        self._limit = limit
        super().__init__(cache_dir, _CACHE_FILENAME, f"registry.huggingface.{backend.value}")

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        return load_catalog_cache(self._cache_path, _CACHE_TTL_SECONDS)

    def _fetch_from_network(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch GGUF-tagged models from the Hugging Face Hub API."""
        try:
            with create_client(timeout=15.0) as client:
                resp = client.get(
                    _API_URL,
                    params={
                        "filter": "gguf",
                        "sort": "downloads",
                        "direction": "-1",
                        "limit": self._limit,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
            models = [self._parse_entry(item) for item in payload if item.get("id")]
            if models:
                save_catalog_cache(self._cache_path, models)
                self._logger.info("Fetched %d GGUF models from the Hugging Face Hub", len(models))
            return models
        except Exception as exc:
            self._logger.debug("Network fetch failed: %s", exc)
            return None

    @staticmethod
    def _parse_entry(item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the fields we need from one Hub API model entry."""
        return {
            "repo_id": item.get("id", ""),
            "pipeline_tag": item.get("pipeline_tag"),
            "tags": item.get("tags", []),
        }

    def _to_spec(self, raw: Dict[str, Any]) -> ModelSpec:
        """Convert one Hub entry to a ModelSpec tagged for this provider's backend."""
        repo_id = raw["repo_id"]
        pipeline_tag = raw.get("pipeline_tag")
        tags = raw.get("tags", [])

        category = _detect_category(repo_id, pipeline_tag, tags)
        capabilities = _detect_capabilities(pipeline_tag, tags)
        short_name = repo_id.split("/")[-1]

        return ModelSpec(
            name=repo_id,
            aliases=[repo_id, short_name],
            category=category,
            capabilities=capabilities,
            default_tag="latest",
            description=f"{repo_id} — GGUF model on the Hugging Face Hub.",
            backend_hints=[self._backend],
        )

    # --- runtime-facing convenience ----------------------------------------

    def models_for_category(self, category: Category) -> List[ModelRef]:
        """Live Hub models for ``category``, as ``ModelRef``s for this backend."""
        return [
            ModelRef.parse(spec.name, backend=self._backend) for spec in self.by_category(category)
        ]

    def models_for_capability(self, capability: Capability) -> List[ModelRef]:
        """Live Hub models exposing ``capability``, as ``ModelRef``s for this backend."""
        return [
            ModelRef.parse(spec.name, backend=self._backend)
            for spec in self.list_all()
            if capability in spec.capabilities
        ]


__all__ = ["HuggingFaceCatalogProvider", "SUPPORTED_BACKENDS"]
