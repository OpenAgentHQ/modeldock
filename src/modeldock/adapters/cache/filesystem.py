"""FilesystemCache — tracks installed/downloaded artifacts.

Manifest records ``ref -> {tag, size, sha256, pulled_at, source}``. Content
hashing (SHA-256) makes the cache self-validating. See Architecture.md §8.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from modeldock.common.errors import CacheError
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef


class FilesystemCache:
    """Filesystem-backed cache with a JSON manifest."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._manifest_path = self._cache_dir / "manifest.json"
        self._logger = get_logger("cache.filesystem")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # --- manifest I/O ----------------------------------------------------

    def _read_manifest(self) -> Dict[str, Any]:
        if not self._manifest_path.exists():
            return {"entries": {}}
        try:
            with self._manifest_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {"entries": {}}
        except (json.JSONDecodeError, OSError) as exc:
            raise CacheError(f"Corrupt manifest: {exc}") from exc

    def _write_manifest(self, data: Dict[str, Any]) -> None:
        tmp = self._manifest_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        tmp.replace(self._manifest_path)

    @staticmethod
    def _key(ref: ModelRef) -> str:
        return f"{ref.name}:{ref.tag}"

    # --- CachePort --------------------------------------------------------

    def is_fresh(self, ref: ModelRef) -> bool:
        data = self._read_manifest()
        entry = data.get("entries", {}).get(self._key(ref))
        return entry is not None

    def record(self, ref: ModelRef, tag: str, sha256: str, size_bytes: int) -> None:
        data = self._read_manifest()
        data.setdefault("entries", {})[self._key(ref)] = {
            "name": ref.name,
            "tag": tag,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "pulled_at": int(time.time()),
            "source": ref.backend.value if ref.backend else "unknown",
        }
        self._write_manifest(data)

    def get_record(self, ref: ModelRef) -> Optional[Dict[str, Any]]:
        data = self._read_manifest()
        entry = data.get("entries", {}).get(self._key(ref))
        return cast(Optional[Dict[str, Any]], entry)

    def clean(self, force: bool = False) -> List[str]:
        removed: List[str] = []
        data = self._read_manifest()
        entries = data.get("entries", {})
        for key, entry in list(entries.items()):
            # Safe default: only drop entries that are corrupt/partial (missing
            # the fields we recorded). ModelDock does not manage the model blobs
            # for Ollama, so a missing artifact file is NOT grounds for removal.
            # force=True wipes every entry.
            if force or not isinstance(entry, dict) or not entry.get("sha256"):
                removed.append(key)
                del entries[key]
        if removed:
            self._write_manifest(data)
        return removed

    def status(self) -> List[Dict[str, Any]]:
        data = self._read_manifest()
        return list(data.get("entries", {}).values())

    def path(self) -> str:
        """Return the cache directory path."""
        return str(self._cache_dir)

    # --- content hashing helper -------------------------------------------

    @staticmethod
    def sha256_of(path: Path, chunk_size: int = 1024 * 1024) -> str:
        """Compute SHA-256 of a file, streaming to bound memory."""
        h = hashlib.sha256()
        with Path(path).open("rb") as fh:
            for chunk in iter(lambda: fh.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()


__all__ = ["FilesystemCache"]
