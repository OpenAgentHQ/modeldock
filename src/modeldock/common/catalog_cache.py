"""Generic TTL'd JSON disk cache for live model-catalog providers.

Extracted from ``adapters/registry/ollama_library.py`` so every live catalog
source (Ollama today; Hugging Face, LM Studio, etc. in the future) shares one
cache implementation instead of reimplementing atomic writes and expiry.
See Architecture.md §9.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def save_catalog_cache(cache_path: Path, models: List[Dict[str, Any]]) -> None:
    """Write ``models`` to ``cache_path`` as a timestamped JSON payload.

    Uses a write-to-temp-then-replace sequence so a crash mid-write can never
    leave a corrupt cache file behind.
    """
    data = {
        "version": 1,
        "scraped_at": time.time(),
        "models": models,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(cache_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()


def load_catalog_cache(cache_path: Path, ttl_seconds: int) -> Optional[List[Dict[str, Any]]]:
    """Read cached models from ``cache_path`` if present and within ``ttl_seconds``.

    Returns ``None`` when the cache is missing, expired, or corrupt.
    """
    if not cache_path.exists():
        return None
    try:
        raw: Dict[str, Any] = json.loads(cache_path.read_text(encoding="utf-8"))
        scraped_at = raw.get("scraped_at", 0)
        if time.time() - scraped_at > ttl_seconds:
            return None
        models: List[Dict[str, Any]] = raw.get("models", [])
        return models
    except (json.JSONDecodeError, KeyError):
        return None


__all__ = ["save_catalog_cache", "load_catalog_cache"]
