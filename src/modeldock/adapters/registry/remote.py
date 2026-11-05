"""RemoteRegistry — the bundled catalog refreshed from a remote URL.

Community catalogs move faster than releases: a model published today is
discoverable only once a new ModelDock version ships an updated
``catalog.json``. ``RemoteRegistry`` closes that gap. It fetches a
catalog.json-shaped document from a URL, caches it on disk with a TTL, and
merges it *over* the bundled catalog — so discovery gains the fresh entries
without ever losing the shipped ones, and keeps working offline from the
cache. Built on ``CachedCatalogRegistry``, the shared fetch → cache → index
pipeline every live catalog source uses. See Architecture.md §9/§14.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from modeldock.adapters.registry.base import CachedCatalogRegistry
from modeldock.adapters.registry.bundled import BundledRegistry, catalog_entry_to_spec
from modeldock.common.catalog_cache import load_catalog_cache, save_catalog_cache
from modeldock.common.errors import ConfigError
from modeldock.common.http import create_client
from modeldock.common.platform import default_cache_dir
from modeldock.domain.model import ModelSpec
from modeldock.domain.source import REMOTE, SourceInfo, SourceTrust

_CACHE_FILENAME = "remote_catalog_cache.json"
#: Shorter than the Ollama catalog's 24h: the point of a remote catalog is
#: freshness, and ``modeldock sources refresh`` bypasses the TTL on demand.
_CACHE_TTL_SECONDS = 3600  # 1 hour
_FETCH_TIMEOUT = 15.0
_MAX_CATALOG_BYTES = 8 * 1024 * 1024  # 8 MiB
#: Sentinel TTL meaning "accept the cache at any age". Used only once a live
#: fetch has already failed, where a stale catalog still beats no catalog.
_ANY_AGE_SECONDS = sys.maxsize
_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _validate_url(url: str) -> str:
    """Return ``url`` when it is a usable http(s) catalog URL, else raise.

    The URL comes from user configuration and is fetched unattended, so the
    scheme is checked up front: ``file://`` and friends would turn a config
    typo into a local-filesystem read.
    """
    candidate = (url or "").strip()
    if not candidate:
        raise ConfigError("registry_url is empty; set a catalog URL to use the remote registry")
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ConfigError(f"Invalid registry_url {url!r}; expected an http:// or https:// URL")
    if not parsed.netloc:
        raise ConfigError(f"Invalid registry_url {url!r}; missing a host")
    return candidate


class RemoteRegistry(CachedCatalogRegistry):
    """Registry that overlays a remotely fetched catalog onto the bundled one.

    The remote entries are cached on disk and read back for
    :data:`_CACHE_TTL_SECONDS` before the network is consulted again, so
    ordinary commands pay no round-trip and keep working offline. A remote
    entry wins over a bundled entry of the same name — fresher metadata is the
    whole reason the remote catalog exists — but a bundled model is never
    dropped, so configuring a remote URL can only ever add to discovery.
    """

    def __init__(
        self,
        url: str,
        fallback: Optional[BundledRegistry] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self._url = _validate_url(url)
        self._fallback = fallback or BundledRegistry()
        self._remote_count = 0
        self._remote_available = False
        super().__init__(
            cache_dir or default_cache_dir(),
            _CACHE_FILENAME,
            "registry.remote",
            source_name=REMOTE,
            source_trust=SourceTrust.CUSTOM,
        )

    # --- fetch → cache → index pipeline ------------------------------------

    def _load(self) -> None:
        """Index the bundled catalog, then overlay whatever the remote offers.

        Overrides the base pipeline because the remote catalog is an *overlay*,
        not a standalone source: a failed fetch with no usable cache must still
        leave the shipped catalog fully intact rather than yield an empty index.
        """
        self._build_index(self._remote_entries())

    def _remote_entries(self) -> List[Dict[str, Any]]:
        """A fresh cache if there is one, else the network, else a stale cache.

        Deliberately cache-*first*, unlike the network-first order a scraped
        catalog uses: this registry is constructed on every CLI invocation, so
        checking the network each time would put a round-trip in front of every
        ``search``/``list``. Inside the TTL the cache answers on its own, and
        ``refresh()`` bypasses it to force a live fetch.
        """
        cached = self._load_cache()
        if cached is not None:
            self._logger.debug("Serving %d remote entries from cache", len(cached))
            return cached
        models = self._fetch_from_network()
        if models is not None:
            return models
        stale = load_catalog_cache(self._cache_path, _ANY_AGE_SECONDS)
        if stale is not None:
            self._logger.info(
                "Remote catalog %s unreachable; serving %d entries from an expired cache",
                self._url,
                len(stale),
            )
            return stale
        self._logger.warning(
            "Remote catalog %s unavailable and no usable cache; serving the bundled catalog only",
            self._url,
        )
        return []

    def _build_index(self, models: List[Dict[str, Any]]) -> None:
        """Index the bundled catalog first, then overlay the remote entries.

        A single malformed remote entry is skipped with a warning instead of
        discarding the whole payload — one bad record in a community feed must
        not cost users every other model in it.
        """
        for spec in self._fallback.list_all():
            self._index_spec(spec)
        indexed = 0
        for raw in models:
            try:
                spec = self._to_spec(raw)
            except Exception as exc:  # noqa: BLE001 - one bad entry must not sink the rest
                self._logger.warning("Skipping malformed remote catalog entry (%s)", exc)
                continue
            if spec.source is None:
                spec.source = self._source_name
            self._index_spec(spec)
            indexed += 1
        self._remote_count = indexed
        self._remote_available = indexed > 0

    def _index_spec(self, spec: ModelSpec) -> None:
        """Add ``spec`` to the name/alias indexes, replacing any earlier entry.

        Looking the previous entry up by lowercased name keeps a remote entry
        that differs from a bundled one only in casing from leaving a stale
        duplicate behind in ``list_all()``.
        """
        previous = self._by_alias.get(spec.name.lower())
        if previous is not None and previous != spec.name:
            self._specs.pop(previous, None)
        self._specs[spec.name] = spec
        for alias in spec.aliases:
            self._by_alias[alias.lower()] = spec.name
        self._by_alias[spec.name.lower()] = spec.name

    def _fetch_from_network(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch the remote catalog, writing it to the cache on success.

        Returns ``None`` on any failure — bad status, oversized body, invalid
        JSON — so the caller falls back to the cache and then to bundled.
        """
        try:
            client = create_client(timeout=_FETCH_TIMEOUT)
            with client, client.stream("GET", self._url) as resp:
                resp.raise_for_status()
                payload = self._read_capped(resp)
            data = json.loads(payload)
            if not isinstance(data, dict) or not isinstance(data.get("models"), list):
                raise ValueError("catalog payload has no 'models' list")
            models: List[Dict[str, Any]] = [m for m in data["models"] if isinstance(m, dict)]
            save_catalog_cache(self._cache_path, models)
            self._logger.info("Fetched %d models from %s", len(models), self._url)
            return models
        except Exception as exc:  # noqa: BLE001 - being offline is normal, never fatal
            self._logger.debug("Remote catalog fetch failed (%s): %s", self._url, exc)
            return None

    @staticmethod
    def _read_capped(resp: httpx.Response) -> bytes:
        """Read a streamed body, refusing to buffer more than the size cap.

        The URL is user-supplied, so the response is streamed and counted
        rather than trusted: neither a misconfigured host nor a hostile one
        gets to exhaust memory through ``resp.json()``.
        """
        declared = resp.headers.get("Content-Length", "")
        if declared.isdigit() and int(declared) > _MAX_CATALOG_BYTES:
            raise ValueError(f"catalog exceeds the {_MAX_CATALOG_BYTES} byte limit")
        chunks: List[bytes] = []
        total = 0
        for chunk in resp.iter_bytes():
            total += len(chunk)
            if total > _MAX_CATALOG_BYTES:
                raise ValueError(f"catalog exceeds the {_MAX_CATALOG_BYTES} byte limit")
            chunks.append(chunk)
        return b"".join(chunks)

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        return load_catalog_cache(self._cache_path, _CACHE_TTL_SECONDS)

    def _to_spec(self, raw: Dict[str, Any]) -> ModelSpec:
        """Convert one catalog.json-shaped remote entry into a ``ModelSpec``."""
        return catalog_entry_to_spec(raw)

    # --- RegistryPort -------------------------------------------------------

    def describe(self) -> List[SourceInfo]:
        """Describe the remote source, then the bundled catalog merged under it.

        ``model_count``/``available`` report the *remote* contribution only:
        the bundled entries beneath are described by their own source, so
        counting them here would overstate what the URL actually provided.
        """
        remote = SourceInfo(
            name=REMOTE,
            trust=SourceTrust.CUSTOM,
            live=True,
            backend=None,
            model_count=self._remote_count,
            cache_path=str(self._cache_path),
            available=self._remote_available,
        )
        return [remote, *self._fallback.describe()]


__all__ = ["RemoteRegistry"]
