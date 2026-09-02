"""Unit tests for the content-addressed blob store (issue #59).

Covers the invariant that matters: identical weights are stored exactly once,
no matter how many refs point at them, and the bytes are only reclaimed when
the last ref goes away.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, List, Optional

import pytest

from modeldock.adapters.cache import FilesystemCache
from modeldock.common.config import Settings
from modeldock.common.errors import CacheError
from modeldock.domain.model import Category, ModelRef, ModelSpec, ModelVariant
from modeldock.ports.cache import CachePort, ContentStorePort

WEIGHTS = b"gguf-weights-payload"
DIGEST = hashlib.sha256(WEIGHTS).hexdigest()
OTHER_WEIGHTS = b"a different quantization"
OTHER_DIGEST = hashlib.sha256(OTHER_WEIGHTS).hexdigest()


def _artifact(tmp_path: Path, name: str, data: bytes = WEIGHTS) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _blobs(cache_dir: Path) -> List[Path]:
    """Every file in the blob store, sorted for stable assertions."""
    blobs_dir = cache_dir / "blobs"
    if not blobs_dir.is_dir():
        return []
    return sorted(p for p in blobs_dir.rglob("*") if p.is_file())


# ─── Port conformance ───────────────────────────────────────────────────────


def test_filesystem_cache_is_a_content_store(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    assert isinstance(cache, ContentStorePort)
    # Still a plain cache — the blob store is additive.
    assert isinstance(cache, CachePort)


def test_fake_cache_is_not_a_content_store(fake_cache: Any) -> None:
    """A manifest-only cache must be detectable so callers can fall back."""
    assert not isinstance(fake_cache, ContentStorePort)


# ─── Blob addressing ────────────────────────────────────────────────────────


def test_blob_path_is_sharded_by_digest(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    assert cache.blob_path(DIGEST) == tmp_path / "blobs" / DIGEST[:2] / DIGEST


def test_blob_path_accepts_uppercase_digest(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    assert cache.blob_path(DIGEST.upper()) == cache.blob_path(DIGEST)


def test_blob_path_rejects_non_digest(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    with pytest.raises(CacheError):
        cache.blob_path("not-a-digest")


def test_has_blob_is_false_for_unknown_and_invalid(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    assert not cache.has_blob(DIGEST)
    assert not cache.has_blob("")
    assert not cache.has_blob("deadbeef")


# ─── store_blob ─────────────────────────────────────────────────────────────


def test_store_blob_moves_artifact_to_its_digest(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path / "cache")
    src = _artifact(tmp_path, "download.gguf")

    blob, digest = cache.store_blob(src)

    assert digest == DIGEST
    assert blob == cache.blob_path(DIGEST)
    assert blob.read_bytes() == WEIGHTS
    assert not src.exists(), "the staged download should be moved, not copied"
    assert cache.has_blob(DIGEST)


def test_identical_weights_are_stored_once(tmp_path: Path) -> None:
    """The whole point of issue #59: no duplicate weights on disk."""
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    first = _artifact(tmp_path, "a/model.gguf")
    second = _artifact(tmp_path, "b/model.gguf")

    blob_a, digest_a = cache.store_blob(first)
    blob_b, digest_b = cache.store_blob(second)

    assert (blob_a, digest_a) == (blob_b, digest_b)
    assert len(_blobs(cache_dir)) == 1
    assert not second.exists(), "the duplicate download should be discarded"


def test_different_weights_get_separate_blobs(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)

    cache.store_blob(_artifact(tmp_path, "a.gguf", WEIGHTS))
    cache.store_blob(_artifact(tmp_path, "b.gguf", OTHER_WEIGHTS))

    assert len(_blobs(cache_dir)) == 2
    assert cache.has_blob(DIGEST)
    assert cache.has_blob(OTHER_DIGEST)


def test_store_blob_verifies_expected_digest(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    src = _artifact(tmp_path, "tampered.gguf")

    with pytest.raises(CacheError, match="SHA-256 mismatch"):
        cache.store_blob(src, sha256=OTHER_DIGEST)

    assert _blobs(cache_dir) == [], "a mismatching artifact must not enter the store"
    assert src.exists(), "the artifact is left alone so the caller can inspect it"


def test_store_blob_accepts_matching_expected_digest(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path / "cache")
    blob, digest = cache.store_blob(_artifact(tmp_path, "model.gguf"), sha256=DIGEST.upper())
    assert digest == DIGEST
    assert blob.read_bytes() == WEIGHTS


def test_store_blob_missing_source_raises(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path / "cache")
    with pytest.raises(CacheError, match="missing artifact"):
        cache.store_blob(tmp_path / "nope.gguf")


# ─── link_into ──────────────────────────────────────────────────────────────


def test_link_into_exposes_blob_at_readable_path(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    blob, _ = cache.store_blob(_artifact(tmp_path, "model.gguf"))
    dest = cache_dir / "models" / "llama3" / "latest.gguf"

    assert cache.link_into(blob, dest) == dest
    assert dest.read_bytes() == WEIGHTS
    # The link is not a second copy in the store.
    assert len(_blobs(cache_dir)) == 1


def test_link_into_is_idempotent(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    blob, _ = cache.store_blob(_artifact(tmp_path, "model.gguf"))
    dest = cache_dir / "models" / "llama3" / "latest.gguf"

    cache.link_into(blob, dest)
    cache.link_into(blob, dest)

    assert dest.read_bytes() == WEIGHTS


def test_link_into_replaces_a_stale_destination(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    blob, _ = cache.store_blob(_artifact(tmp_path, "model.gguf"))
    dest = cache_dir / "models" / "llama3" / "latest.gguf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"stale leftovers")

    cache.link_into(blob, dest)

    assert dest.read_bytes() == WEIGHTS


def test_link_into_falls_back_to_copy_without_hard_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filesystems without hard links still get a usable artifact."""
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    blob, _ = cache.store_blob(_artifact(tmp_path, "model.gguf"))
    dest = cache_dir / "models" / "llama3" / "latest.gguf"

    def _no_links(*args: Any, **kwargs: Any) -> None:
        raise OSError("hard links unsupported")

    monkeypatch.setattr(os, "link", _no_links)

    cache.link_into(blob, dest)

    assert dest.read_bytes() == WEIGHTS


def test_link_into_missing_blob_raises(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path / "cache")
    with pytest.raises(CacheError, match="missing blob"):
        cache.link_into(tmp_path / "gone", tmp_path / "dest.gguf")


# ─── Manifest bookkeeping and reclamation ───────────────────────────────────


def _install(cache: FilesystemCache, cache_dir: Path, name: str, data: bytes = WEIGHTS) -> Path:
    """Store ``data`` for ``name`` the way the manager does, return the artifact."""
    ref = ModelRef.parse(name)
    blob, digest = cache.store_blob(_artifact(cache_dir / "staging", f"{name}.gguf", data))
    dest = cache_dir / "models" / name / f"{ref.tag}.gguf"
    cache.link_into(blob, dest)
    cache.record_artifact(ref, ref.tag, digest, blob.stat().st_size, dest)
    return dest


def test_record_artifact_stores_blob_digest_and_path(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    dest = _install(cache, cache_dir, "llama3")

    record = cache.get_record(ModelRef.parse("llama3"))
    assert record is not None
    assert record["blob"] == DIGEST
    assert record["sha256"] == DIGEST
    assert record["path"] == str(dest)
    assert record["size_bytes"] == len(WEIGHTS)


def test_evict_removes_artifact_and_reclaims_the_blob(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    dest = _install(cache, cache_dir, "llama3")

    cache.evict(ModelRef.parse("llama3"))

    assert not dest.exists()
    assert _blobs(cache_dir) == []
    assert cache.status() == []


def test_shared_blob_survives_until_the_last_ref_is_evicted(tmp_path: Path) -> None:
    """Reference counting: one ref's removal must not break the other."""
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    first = _install(cache, cache_dir, "llama3")
    second = _install(cache, cache_dir, "llama3-clone")
    assert len(_blobs(cache_dir)) == 1

    cache.evict(ModelRef.parse("llama3"))

    assert not first.exists()
    assert second.read_bytes() == WEIGHTS, "the surviving ref still resolves"
    assert len(_blobs(cache_dir)) == 1

    cache.evict(ModelRef.parse("llama3-clone"))

    assert _blobs(cache_dir) == []


def test_evict_without_a_blob_entry_is_a_noop(tmp_path: Path) -> None:
    """Entries recorded before the blob store existed still evict cleanly."""
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("llama3")
    cache.record(ref, "latest", "deadbeef", 1)

    cache.evict(ref)

    assert cache.status() == []


def test_clean_prunes_orphan_blobs(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    _install(cache, cache_dir, "llama3")
    # A blob nothing references — e.g. an interrupted install.
    cache.store_blob(_artifact(tmp_path, "orphan.gguf", OTHER_WEIGHTS))
    assert len(_blobs(cache_dir)) == 2

    removed = cache.clean()

    assert removed == [f"blobs/{OTHER_DIGEST}"]
    assert len(_blobs(cache_dir)) == 1
    assert cache.has_blob(DIGEST), "referenced weights are never pruned"


def test_clean_force_wipes_entries_artifacts_and_blobs(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    dest = _install(cache, cache_dir, "llama3")

    removed = cache.clean(force=True)

    assert "llama3:latest" in removed
    assert f"blobs/{DIGEST}" in removed
    assert not dest.exists()
    assert _blobs(cache_dir) == []


def test_clean_removes_the_artifact_of_a_corrupt_entry(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = FilesystemCache(cache_dir)
    dest = _install(cache, cache_dir, "llama3")
    data = cache._read_manifest()
    data["entries"]["llama3:latest"].pop("sha256")
    cache._write_manifest(data)

    cache.clean()

    assert not dest.exists()
    assert _blobs(cache_dir) == []


# ─── Manager wiring ─────────────────────────────────────────────────────────


class _CountingDownloader:
    """Stands in for HttpDownloader: writes the payload, counts the calls."""

    def __init__(self, payload: bytes = WEIGHTS) -> None:
        self.payload = payload
        self.calls: List[Path] = []

    def download(self, spec: ModelSpec, dest: Path, progress: Any = None) -> Path:
        self.calls.append(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.payload)
        return dest


def _spec(name: str, sha256: Optional[str] = None) -> ModelSpec:
    return ModelSpec(
        name=name,
        category=Category.CHAT,
        default_tag="latest",
        variants=[
            ModelVariant(
                tag="latest",
                download_url=f"https://example.com/{name}.gguf",
                sha256=sha256,
            )
        ],
    )


def _manager(
    tmp_path: Path,
    specs: List[ModelSpec],
    downloader: _CountingDownloader,
    fake_registry: Any,
    fake_runtime: Any,
) -> Any:
    from modeldock.core.manager import ModelManager

    fake_registry.specs = list(specs)
    fake_registry.by_name = {spec.name: spec for spec in specs}
    manager = ModelManager(
        settings=Settings(cache_dir=tmp_path),
        registry=fake_registry,
        runtime=fake_runtime,
        cache=FilesystemCache(tmp_path),
    )
    manager._http_downloader = downloader
    return manager


def test_install_stores_weights_content_addressed(
    tmp_path: Path, fake_registry: Any, fake_runtime: Any
) -> None:
    downloader = _CountingDownloader()
    manager = _manager(tmp_path, [_spec("llama3")], downloader, fake_registry, fake_runtime)

    manager.install("llama3")

    assert len(_blobs(tmp_path)) == 1
    artifact = tmp_path / "models" / "llama3" / "latest.gguf"
    assert artifact.read_bytes() == WEIGHTS
    record = manager.cache.status()[0]
    assert record["blob"] == DIGEST


def test_two_models_with_identical_weights_share_one_blob(
    tmp_path: Path, fake_registry: Any, fake_runtime: Any
) -> None:
    """Different names, same bytes — the catalog publishes no digest."""
    downloader = _CountingDownloader()
    manager = _manager(
        tmp_path,
        [_spec("llama3"), _spec("llama3-mirror")],
        downloader,
        fake_registry,
        fake_runtime,
    )

    manager.install("llama3")
    manager.install("llama3-mirror")

    assert len(downloader.calls) == 2, "without a published digest both must be fetched"
    assert len(_blobs(tmp_path)) == 1, "but the weights are stored only once"
    assert (tmp_path / "models" / "llama3" / "latest.gguf").read_bytes() == WEIGHTS
    assert (tmp_path / "models" / "llama3-mirror" / "latest.gguf").read_bytes() == WEIGHTS


def test_install_skips_the_download_when_the_digest_is_already_stored(
    tmp_path: Path, fake_registry: Any, fake_runtime: Any
) -> None:
    """A published digest turns a duplicate install into a link — no network."""
    downloader = _CountingDownloader()
    manager = _manager(
        tmp_path,
        [_spec("llama3", sha256=DIGEST), _spec("llama3-mirror", sha256=DIGEST)],
        downloader,
        fake_registry,
        fake_runtime,
    )

    manager.install("llama3")
    manager.install("llama3-mirror")

    assert len(downloader.calls) == 1, "the second install must not re-download"
    assert len(_blobs(tmp_path)) == 1
    assert (tmp_path / "models" / "llama3-mirror" / "latest.gguf").read_bytes() == WEIGHTS


def test_reinstalling_the_same_ref_does_not_duplicate_weights(
    tmp_path: Path, fake_registry: Any, fake_runtime: Any
) -> None:
    downloader = _CountingDownloader()
    manager = _manager(tmp_path, [_spec("llama3")], downloader, fake_registry, fake_runtime)

    manager.install("llama3")
    manager.install("llama3")

    assert len(_blobs(tmp_path)) == 1
    assert len(manager.cache.status()) == 1


def test_install_rejects_weights_that_do_not_match_the_catalog_digest(
    tmp_path: Path, fake_registry: Any, fake_runtime: Any
) -> None:
    downloader = _CountingDownloader(payload=OTHER_WEIGHTS)
    manager = _manager(
        tmp_path, [_spec("llama3", sha256=DIGEST)], downloader, fake_registry, fake_runtime
    )

    with pytest.raises(CacheError, match="SHA-256 mismatch"):
        manager.install("llama3")

    assert _blobs(tmp_path) == []
