"""Unit tests for CacheService and FilesystemCache."""

from __future__ import annotations

from pathlib import Path

import pytest

from modeldock.adapters.cache import FilesystemCache
from modeldock.common.errors import CacheError
from modeldock.core.cache import CacheService
from modeldock.domain.model import ModelRef


def test_cache_service_record_and_fresh(fake_cache: object) -> None:
    svc = CacheService(fake_cache)
    ref = ModelRef.parse("llama3")
    assert not svc.is_fresh(ref)
    svc.record(ref, "latest", "abc", 10)
    assert svc.is_fresh(ref)


def test_cache_service_status_and_clean(fake_cache: object) -> None:
    svc = CacheService(fake_cache)
    ref = ModelRef.parse("llama3")
    svc.record(ref, "latest", "abc", 10)
    assert len(svc.status()) == 1
    # Safe default keeps a valid entry.
    assert svc.clean() == []
    assert len(svc.status()) == 1
    # force=True wipes it.
    assert svc.clean(force=True)
    assert svc.status() == []


def test_filesystem_cache_roundtrip(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("qwen3:8b")
    assert not cache.is_fresh(ref)
    cache.record(ref, "8b", "deadbeef", 1024)
    assert cache.is_fresh(ref)
    rec = cache.get_record(ref)
    assert rec is not None
    assert rec["sha256"] == "deadbeef"
    assert rec["size_bytes"] == 1024


def test_filesystem_cache_persists_across_instances(tmp_path: Path) -> None:
    ref = ModelRef.parse("llama3")
    FilesystemCache(tmp_path).record(ref, "latest", "x", 1)
    again = FilesystemCache(tmp_path)
    assert again.is_fresh(ref)


def test_filesystem_cache_clean_keeps_valid_entries_by_default(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("llama3")
    cache.record(ref, "latest", "x", 1)
    # Safe default: a valid entry is kept even though no .bin artifact exists.
    assert cache.clean() == []
    assert cache.is_fresh(ref)


def test_filesystem_cache_clean_removes_corrupt_entries(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("llama3")
    cache.record(ref, "latest", "x", 1)
    # Corrupt an entry (drop sha256) to simulate a partial/corrupt record.
    data = cache._read_manifest()
    data["entries"]["llama3:latest"].pop("sha256")
    cache._write_manifest(data)
    removed = cache.clean()
    assert removed == ["llama3:latest"]
    assert cache.status() == []


def test_filesystem_cache_clean_force_wipes_all(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("llama3")
    cache.record(ref, "latest", "x", 1)
    removed = cache.clean(force=True)
    assert removed == ["llama3:latest"]
    assert cache.status() == []


def test_cache_service_clean_passes_force(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    ref = ModelRef.parse("llama3")
    cache.record(ref, "latest", "x", 1)
    svc = CacheService(cache)
    assert svc.clean() == []
    assert svc.clean(force=True) == ["llama3:latest"]


def test_filesystem_cache_corrupt_manifest_raises(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{not valid json")
    cache = FilesystemCache(tmp_path)
    with pytest.raises(CacheError):
        cache.is_fresh(ModelRef.parse("llama3"))


def test_filesystem_cache_sha256(tmp_path: Path) -> None:
    f = tmp_path / "blob.bin"
    f.write_bytes(b"hello world")
    digest = FilesystemCache.sha256_of(f)
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_cache_service_path_returns_real_dir(tmp_path: Path) -> None:
    svc = CacheService(FilesystemCache(tmp_path))
    assert svc.path() == str(tmp_path)


def test_filesystem_cache_path_returns_cache_dir(tmp_path: Path) -> None:
    cache = FilesystemCache(tmp_path)
    assert cache.path() == str(tmp_path)
