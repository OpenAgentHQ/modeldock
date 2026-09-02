"""FilesystemCache — tracks installed/downloaded artifacts.

Manifest records ``ref -> {tag, size, sha256, pulled_at, source}``. Content
hashing (SHA-256) makes the cache self-validating.

Downloaded weights live in a content-addressed blob store
(``blobs/<sha256[:2]>/<sha256>``) and are exposed at their human-readable
``models/<name>/<tag>.gguf`` path through a hard link, so byte-identical
weights occupy disk exactly once no matter how many refs point at them.
Blobs are reference-counted through the manifest: evicting one ref never
deletes weights another ref still uses. See Architecture.md §8.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from modeldock.common.errors import CacheError
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef

#: Sub-directory of the cache holding content-addressed weights.
_BLOBS_DIRNAME = "blobs"

_HEX_DIGITS = frozenset("0123456789abcdef")

#: Grace period before an unreferenced blob may be pruned. Covers the window
#: between ``store_blob`` and ``record_artifact`` so a concurrent ``clean()``
#: cannot delete weights an in-flight install has not registered yet.
_ORPHAN_GRACE_SECONDS = 300


class FilesystemCache:
    """Filesystem-backed cache with a JSON manifest and a blob store."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._manifest_path = self._cache_dir / "manifest.json"
        self._blobs_dir = self._cache_dir / _BLOBS_DIRNAME
        self._logger = get_logger("cache.filesystem")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_tmp_files()

    def _cleanup_tmp_files(self) -> None:
        for tmp in self._cache_dir.rglob("*.tmp"):
            if tmp.name == "manifest.tmp":
                continue
            try:
                tmp.unlink()
                self._logger.debug("Removed stale temp file: %s", tmp)
            except OSError as exc:
                self._logger.debug("Could not remove stale temp file %s: %s", tmp, exc)

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
        self._record(ref, tag, sha256, size_bytes)

    def _record(
        self,
        ref: ModelRef,
        tag: str,
        sha256: str,
        size_bytes: int,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = self._read_manifest()
        entries = data.setdefault("entries", {})
        existing = entries.get(self._key(ref), {})
        entry: Dict[str, Any] = {
            "name": ref.name,
            "tag": tag,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "pulled_at": int(time.time()),
            "source": ref.backend.value if ref.backend else "unknown",
        }
        if "user_config" in existing:
            entry["user_config"] = existing["user_config"]
        entry.update(extras or {})
        entries[self._key(ref)] = entry
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
                if isinstance(entry, dict):
                    self._remove_artifact(entry)
        if removed:
            self._write_manifest(data)
        # Weights no surviving entry points at are dead bytes: reclaim them.
        removed.extend(self._prune_orphan_blobs(entries, force=force))
        self._cleanup_tmp_files()
        return removed

    def evict(self, ref: ModelRef) -> None:
        data = self._read_manifest()
        entries = data.get("entries", {})
        entry = entries.pop(self._key(ref), None)
        self._write_manifest(data)
        if not isinstance(entry, dict):
            return
        self._remove_artifact(entry)
        self._gc_blob(str(entry.get("blob") or ""), entries)

    def status(self) -> List[Dict[str, Any]]:
        data = self._read_manifest()
        return list(data.get("entries", {}).values())

    def path(self) -> str:
        """Return the cache directory path."""
        return str(self._cache_dir)

    # --- content hashing helper -------------------------------------------

    def get_model_config(self, ref: ModelRef) -> Optional[Dict[str, Any]]:
        data = self._read_manifest()
        entry = data.get("entries", {}).get(self._key(ref))
        if entry is None:
            return None
        return cast(Optional[Dict[str, Any]], entry.get("user_config"))

    def set_model_config(self, ref: ModelRef, config: Dict[str, Any]) -> None:
        data = self._read_manifest()
        entries = data.setdefault("entries", {})
        entries.setdefault(self._key(ref), {})["user_config"] = config
        self._write_manifest(data)

    @staticmethod
    def sha256_of(path: Path, chunk_size: int = 1024 * 1024) -> str:
        """Compute SHA-256 of a file, streaming to bound memory."""
        h = hashlib.sha256()
        with Path(path).open("rb") as fh:
            for chunk in iter(lambda: fh.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    # --- ContentStorePort: content-addressed blob store --------------------

    def blob_path(self, sha256: str) -> Path:
        """Return the content-addressed location for ``sha256``.

        Sharded on the first two hex digits so a large cache never lands
        thousands of files in a single directory.
        """
        digest = self._normalize_digest(sha256)
        return self._blobs_dir / digest[:2] / digest

    def has_blob(self, sha256: str) -> bool:
        """Return True if weights with this digest are already stored."""
        try:
            blob = self.blob_path(sha256)
        except CacheError:
            return False
        return self._is_stored(blob)

    def store_blob(self, src: Path, sha256: Optional[str] = None) -> Tuple[Path, str]:
        """Move ``src`` into the blob store; return ``(blob_path, digest)``.

        Identical weights are never duplicated: when a blob with the same
        digest is already stored, ``src`` is discarded and the existing blob is
        returned. Pass ``sha256`` to assert the expected digest — a mismatch
        raises ``CacheError`` and leaves the store untouched.
        """
        src = Path(src)
        if not src.is_file():
            raise CacheError(f"Cannot store missing artifact: {src}")
        digest = self.sha256_of(src)
        if sha256:
            expected = self._normalize_digest(sha256)
            if digest != expected:
                raise CacheError(
                    f"SHA-256 mismatch for {src.name} (expected {expected}, got {digest})"
                )
        blob = self.blob_path(digest)
        if self._is_stored(blob):
            self._logger.debug("Reusing stored weights %s for %s", digest[:12], src.name)
            # A reused blob keeps its original mtime, so the orphan grace
            # period would not cover it. Mark it live before the caller gets
            # the chance to record it.
            self._touch(blob)
            src.unlink()
            return blob, digest
        blob.parent.mkdir(parents=True, exist_ok=True)
        self._move(src, blob)
        self._logger.debug("Stored weights %s (%d bytes)", digest[:12], blob.stat().st_size)
        return blob, digest

    def link_into(self, blob: Path, dest: Path) -> Path:
        """Expose ``blob`` at ``dest`` without copying its bytes.

        Uses a hard link so the artifact stays addressable by a readable path
        (what users hand to ``llama-server``) while costing disk only once.
        Filesystems without hard-link support fall back to a plain copy.
        """
        blob = Path(blob)
        dest = Path(dest)
        if not blob.is_file():
            raise CacheError(f"Cannot link missing blob: {blob}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Linking is the "these weights are in use" signal, and it happens on
        # every install path — including the one that skips the download
        # entirely — so it is where the grace period gets refreshed.
        self._touch(blob)
        if dest.exists():
            if self._same_file(dest, blob):
                return dest
            dest.unlink()
        try:
            os.link(blob, dest)
        except (OSError, NotImplementedError) as exc:
            self._logger.debug("Hard link unavailable (%s); copying %s instead", exc, blob.name)
            shutil.copy2(blob, dest)
        return dest

    def record_artifact(
        self,
        ref: ModelRef,
        tag: str,
        sha256: str,
        size_bytes: int,
        path: Path,
    ) -> None:
        """Record a stored artifact, remembering its blob digest and path.

        The digest is what reference-counts the blob; the path is what
        ``evict``/``clean`` unlink when the entry goes away.
        """
        self._record(
            ref,
            tag,
            sha256,
            size_bytes,
            extras={"blob": (sha256 or "").strip().lower(), "path": str(path)},
        )

    # --- blob store internals ---------------------------------------------

    @staticmethod
    def _normalize_digest(sha256: str) -> str:
        digest = (sha256 or "").strip().lower()
        if len(digest) != 64 or not set(digest) <= _HEX_DIGITS:
            raise CacheError(f"Not a valid SHA-256 digest: {sha256!r}")
        return digest

    @staticmethod
    def _is_stored(blob: Path) -> bool:
        try:
            return blob.is_file() and blob.stat().st_size > 0
        except OSError:
            return False

    def _inside_cache(self, path: Path) -> Optional[Path]:
        """Return ``path`` resolved if it lives under the cache dir, else None."""
        try:
            resolved = path.resolve()
            root = self._cache_dir.resolve()
        except OSError:
            return None
        return resolved if resolved.is_relative_to(root) else None

    def _touch(self, path: Path) -> None:
        """Refresh a blob's mtime so the orphan grace period covers it."""
        with contextlib.suppress(OSError):
            os.utime(path, None)

    @staticmethod
    def _older_than(path: Path, cutoff: float) -> bool:
        """Return True if ``path`` was last written before ``cutoff``.

        An unreadable stat means "do not touch it" — never delete on a guess.
        """
        try:
            return path.stat().st_mtime < cutoff
        except OSError:
            return False

    @staticmethod
    def _same_file(left: Path, right: Path) -> bool:
        try:
            return os.path.samefile(left, right)
        except OSError:
            return False

    def _move(self, src: Path, dest: Path) -> None:
        """Move ``src`` onto ``dest``, atomically when on the same volume."""
        try:
            src.replace(dest)
            return
        except OSError as exc:
            self._logger.debug("Rename into blob store failed (%s); copying", exc)
        tmp = dest.with_suffix(".tmp")
        try:
            shutil.copy2(src, tmp)
            tmp.replace(dest)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise CacheError(f"Could not store artifact {src.name}: {exc}") from exc
        src.unlink(missing_ok=True)

    @staticmethod
    def _referenced_digests(entries: Dict[str, Any]) -> Set[str]:
        return {
            str(entry.get("blob") or "").strip().lower()
            for entry in entries.values()
            if isinstance(entry, dict) and entry.get("blob")
        }

    def _remove_artifact(self, entry: Dict[str, Any]) -> None:
        """Unlink the readable artifact path recorded for an entry.

        The manifest is a plain file a user can edit, so its ``path`` is
        untrusted input: only paths inside the cache directory are ever
        unlinked. Anything else — a hand-edited entry, a manifest carried over
        from another cache root — is left alone.
        """
        recorded = entry.get("path")
        if not recorded:
            return
        artifact = self._inside_cache(Path(str(recorded)))
        if artifact is None:
            self._logger.debug("Refusing to remove artifact outside the cache: %s", recorded)
            return
        try:
            artifact.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.debug("Could not remove artifact %s: %s", artifact, exc)
            return
        self._prune_empty_dirs(artifact.parent)

    def _prune_empty_dirs(self, directory: Path) -> None:
        """Drop directories emptied by a removal, never past the cache root."""
        current = directory
        while current != self._cache_dir and self._cache_dir in current.parents:
            with contextlib.suppress(OSError):
                current.rmdir()
            if current.exists():
                return
            current = current.parent

    def _gc_blob(self, digest: str, entries: Dict[str, Any]) -> bool:
        """Delete the blob for ``digest`` unless an entry still references it.

        ``digest`` comes from the manifest, so it is validated rather than
        pasted into a path: a malformed value names no blob we stored and must
        never be able to point outside the blob store.
        """
        digest = (digest or "").strip().lower()
        if not digest or digest in self._referenced_digests(entries):
            return False
        try:
            blob = self.blob_path(digest)
        except CacheError:
            self._logger.debug("Ignoring malformed blob digest in manifest: %r", digest)
            return False
        try:
            blob.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.debug("Could not remove blob %s: %s", digest[:12], exc)
            return False
        self._prune_empty_dirs(blob.parent)
        return True

    def _prune_orphan_blobs(self, entries: Dict[str, Any], force: bool = False) -> List[str]:
        """Remove stored weights no manifest entry references any more.

        A blob becomes referenced only once the install that stored it reaches
        ``record_artifact``. Sweeping unconditionally would let a concurrent
        ``cache clean`` delete weights out from under an install still between
        those two steps, so freshly written blobs are left alone for
        ``_ORPHAN_GRACE_SECONDS``. ``force=True`` is an explicit "wipe
        everything" and skips the grace period.
        """
        if not self._blobs_dir.is_dir():
            return []
        referenced = self._referenced_digests(entries)
        cutoff = time.time() - _ORPHAN_GRACE_SECONDS
        removed: List[str] = []
        for blob in sorted(self._blobs_dir.rglob("*")):
            if not blob.is_file() or blob.name in referenced:
                continue
            if not force and not self._older_than(blob, cutoff):
                self._logger.debug("Keeping recently stored blob %s", blob.name)
                continue
            try:
                blob.unlink()
            except OSError as exc:
                self._logger.debug("Could not remove orphan blob %s: %s", blob, exc)
                continue
            removed.append(f"{_BLOBS_DIRNAME}/{blob.name}")
            self._prune_empty_dirs(blob.parent)
        return removed


__all__ = ["FilesystemCache"]
