"""Tests for RemoteRegistry — a cached remote catalog merged over bundled.

These drive a real HTTP server on a real socket rather than mocking httpx, so
the caching behaviour that matters (how many requests actually leave the
process) is observable. That request count is the point of several tests: a
catalog that re-fetches on every construction would pass a mocked test and
still put a network round-trip in front of every CLI invocation.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List

import pytest

from modeldock.adapters.registry import remote as remote_module
from modeldock.adapters.registry.bundled import BundledRegistry
from modeldock.adapters.registry.composite import CompositeRegistry
from modeldock.adapters.registry.remote import RemoteRegistry
from modeldock.common.config import Settings
from modeldock.common.errors import ConfigError, ModelNotFoundError
from modeldock.core.manager import ModelManager
from modeldock.domain.model import Category, ModelRef, RuntimeBackend
from modeldock.domain.source import BUNDLED, REMOTE, SourceTrust

# ---------------------------------------------------------------------------
# Catalog fixtures
# ---------------------------------------------------------------------------

#: A model published after the last release — the case the remote catalog exists for.
FRESH_MODEL: Dict[str, Any] = {
    "name": "brand-new-model",
    "aliases": ["shiny", "Brand-New"],
    "category": "chat",
    "capabilities": ["chat", "tool_use"],
    "default_tag": "latest",
    "description": "Published after the last ModelDock release.",
    "backend_hints": ["ollama"],
    "variants": [{"tag": "latest", "params": "7B"}, {"tag": "70b", "params": "70B"}],
}

#: Same name as a bundled entry, with metadata the shipped catalog cannot have.
UPDATED_LLAMA3: Dict[str, Any] = {
    "name": "llama3",
    "aliases": ["llama-3"],
    "category": "chat",
    "capabilities": ["chat"],
    "default_tag": "latest",
    "description": "Refreshed llama3 description from the remote catalog.",
    "backend_hints": ["ollama"],
}

#: ``category`` is not a member of the Category enum, so coercion raises.
MALFORMED_MODEL: Dict[str, Any] = {"name": "broken", "category": "not-a-real-category"}


def catalog(*models: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap entries in the catalog.json envelope the registry expects."""
    return {"version": 1, "models": list(models)}


# ---------------------------------------------------------------------------
# Stub catalog server
# ---------------------------------------------------------------------------


class StubCatalogServer:
    """A real HTTP server serving one catalog document, counting requests."""

    def __init__(self, payload: Any, status: int = 200) -> None:
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.status = status
        self.hits = 0
        state = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                state.hits += 1
                self.send_response(state.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(state.body)))
                self.end_headers()
                self.wfile.write(state.body)

            def log_message(self, *args: object) -> None:
                """Silence the default stderr access log."""

        self._server = HTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address[0], self._server.server_address[1]
        return f"http://{host}:{port}/catalog.json"

    def stop(self) -> None:
        """Shut the server down; its URL then refuses connections."""
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


@pytest.fixture
def serve() -> Iterator[Callable[..., StubCatalogServer]]:
    """Factory for stub catalog servers, all torn down at test end."""
    started: List[StubCatalogServer] = []

    def _make(payload: Any, status: int = 200) -> StubCatalogServer:
        server = StubCatalogServer(payload, status)
        started.append(server)
        return server

    yield _make
    for server in started:
        server.stop()


@pytest.fixture
def bundled() -> BundledRegistry:
    return BundledRegistry()


def _expire_cache(cache_dir: Path, age_seconds: float) -> Path:
    """Back-date the cache's timestamp so it reads as ``age_seconds`` old."""
    path = cache_dir / "remote_catalog_cache.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scraped_at"] = time.time() - age_seconds
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fetching and indexing
# ---------------------------------------------------------------------------


def test_fetches_and_indexes_remote_models(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert server.hits == 1
    spec = registry.get(ModelRef.parse("brand-new-model"))
    assert spec.description == "Published after the last ModelDock release."
    assert spec.source == REMOTE
    assert registry.versions(ModelRef.parse("brand-new-model")) == ["latest", "70b"]


def test_remote_model_is_discoverable_by_search_and_recommend(serve: Any, tmp_path: Path) -> None:
    """Search is the whole point: a fresh model nobody can find is not published."""
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert [s.name for s in registry.search("brand-new-model")] == ["brand-new-model"]
    assert "brand-new-model" in [s.name for s in registry.recommend("brand-new-model")]
    assert "brand-new-model" in [s.name for s in registry.by_category(Category.CHAT)]


def test_resolves_by_alias_and_ignores_case(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    for probe in ("brand-new-model", "shiny", "BRAND-NEW-MODEL", "Brand-New"):
        assert registry.resolve(ModelRef.parse(probe)).name == "brand-new-model"


def test_unknown_model_still_raises(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    with pytest.raises(ModelNotFoundError):
        registry.get(ModelRef.parse("no-such-model"))
    assert registry.versions(ModelRef.parse("no-such-model")) == []


# ---------------------------------------------------------------------------
# Merging with the bundled catalog
# ---------------------------------------------------------------------------


def test_merges_with_bundled_instead_of_replacing_it(
    serve: Any, tmp_path: Path, bundled: BundledRegistry
) -> None:
    """A successful fetch must add to the catalog, never shrink it."""
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    names = {s.name for s in registry.list_all()}
    assert "brand-new-model" in names
    assert {s.name for s in bundled.list_all()} <= names
    assert len(registry.list_all()) == len(bundled.list_all()) + 1
    # Bundled entries stay reachable through every query path, not just get().
    assert registry.search("llama3")
    assert registry.get(ModelRef.parse("llama-3")).name == "llama3"


def test_remote_entry_wins_a_name_collision(
    serve: Any, tmp_path: Path, bundled: BundledRegistry
) -> None:
    server = serve(catalog(UPDATED_LLAMA3))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    spec = registry.get(ModelRef.parse("llama3"))
    assert spec.description == "Refreshed llama3 description from the remote catalog."
    # Overwritten, not duplicated.
    assert [s.name for s in registry.list_all()].count("llama3") == 1
    assert len(registry.list_all()) == len(bundled.list_all())


def test_malformed_entry_is_skipped_without_losing_the_payload(
    serve: Any, tmp_path: Path, bundled: BundledRegistry
) -> None:
    """One bad record in a community feed must not cost users the whole fetch."""
    server = serve(catalog(FRESH_MODEL, MALFORMED_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    names = {s.name for s in registry.list_all()}
    assert "brand-new-model" in names
    assert "broken" not in names
    assert {s.name for s in bundled.list_all()} <= names


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_second_construction_is_served_from_cache(serve: Any, tmp_path: Path) -> None:
    """Inside the TTL the cache answers alone — no round-trip per CLI command."""
    server = serve(catalog(FRESH_MODEL))
    RemoteRegistry(server.url, cache_dir=tmp_path)
    assert (tmp_path / "remote_catalog_cache.json").exists()
    assert server.hits == 1

    again = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert server.hits == 1
    assert again.get(ModelRef.parse("brand-new-model")).name == "brand-new-model"


def test_expired_cache_triggers_a_refetch(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    RemoteRegistry(server.url, cache_dir=tmp_path)
    _expire_cache(tmp_path, remote_module._CACHE_TTL_SECONDS + 60)

    RemoteRegistry(server.url, cache_dir=tmp_path)

    assert server.hits == 2


def test_unreachable_server_falls_back_to_cache(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    url = server.url
    RemoteRegistry(url, cache_dir=tmp_path)
    _expire_cache(tmp_path, remote_module._CACHE_TTL_SECONDS + 60)
    server.stop()

    registry = RemoteRegistry(url, cache_dir=tmp_path)

    # An expired cache still beats no catalog once the network is gone.
    assert registry.get(ModelRef.parse("brand-new-model")).name == "brand-new-model"


def test_no_server_and_no_cache_degrades_to_bundled(
    serve: Any, tmp_path: Path, bundled: BundledRegistry
) -> None:
    server = serve(catalog(FRESH_MODEL))
    url = server.url
    server.stop()

    registry = RemoteRegistry(url, cache_dir=tmp_path)

    assert {s.name for s in registry.list_all()} == {s.name for s in bundled.list_all()}
    assert registry.get(ModelRef.parse("llama3")).name == "llama3"


def test_error_status_degrades_to_bundled(
    serve: Any, tmp_path: Path, bundled: BundledRegistry
) -> None:
    server = serve(catalog(FRESH_MODEL), status=500)

    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert len(registry.list_all()) == len(bundled.list_all())
    assert not (tmp_path / "remote_catalog_cache.json").exists()


@pytest.mark.parametrize("body", [b"not json at all", b'{"nope": []}', b"[]"])
def test_unusable_payload_degrades_to_bundled(
    serve: Any, tmp_path: Path, bundled: BundledRegistry, body: bytes
) -> None:
    server = serve(body)

    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert len(registry.list_all()) == len(bundled.list_all())


def test_oversized_catalog_is_refused(
    serve: Any, tmp_path: Path, bundled: BundledRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user-supplied URL does not get to decide how much memory we buffer."""
    monkeypatch.setattr(remote_module, "_MAX_CATALOG_BYTES", 16)
    server = serve(catalog(FRESH_MODEL))

    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert len(registry.list_all()) == len(bundled.list_all())


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------


def test_refresh_bypasses_the_cache_ttl(serve: Any, tmp_path: Path) -> None:
    """`modeldock sources refresh` must reach the network even on a warm cache."""
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)
    assert server.hits == 1

    total = registry.refresh()

    assert server.hits == 2
    assert total == len(registry.list_all())
    assert registry.get(ModelRef.parse("brand-new-model")).name == "brand-new-model"


def test_refresh_is_discoverable_by_the_composite_and_manager(serve: Any, tmp_path: Path) -> None:
    """The refresh contract is duck-typed, so a private _refresh would be skipped."""
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    assert callable(getattr(registry, "refresh", None))
    CompositeRegistry([registry]).refresh()
    assert server.hits == 2


def test_failed_refresh_keeps_the_existing_index(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)
    before = {s.name for s in registry.list_all()}
    server.stop()

    registry.refresh()

    assert {s.name for s in registry.list_all()} == before


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://example.com/catalog.json", "example.com/catalog.json", "", "   "],
)
def test_rejects_non_http_urls(url: str, tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        RemoteRegistry(url, cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# describe()
# ---------------------------------------------------------------------------


def test_describe_reports_remote_contribution_and_bundled(serve: Any, tmp_path: Path) -> None:
    server = serve(catalog(FRESH_MODEL))
    registry = RemoteRegistry(server.url, cache_dir=tmp_path)

    infos = {info.name: info for info in registry.describe()}
    assert set(infos) == {REMOTE, BUNDLED}
    assert infos[REMOTE].trust == SourceTrust.CUSTOM
    assert infos[REMOTE].available is True
    # The remote count is its own contribution, not the merged total.
    assert infos[REMOTE].model_count == 1
    assert infos[REMOTE].cache_path == str(tmp_path / "remote_catalog_cache.json")


def test_describe_marks_an_unreachable_remote_unavailable(serve: Any, tmp_path: Path) -> None:
    """Reporting the bundled fallback's count as the remote's would be a lie."""
    server = serve(catalog(FRESH_MODEL))
    url = server.url
    server.stop()

    infos = {info.name: info for info in RemoteRegistry(url, cache_dir=tmp_path).describe()}

    assert infos[REMOTE].available is False
    assert infos[REMOTE].model_count == 0


# ---------------------------------------------------------------------------
# ModelManager wiring
# ---------------------------------------------------------------------------


class TestManagerWiring:
    def test_remote_source_uses_the_configured_url(self, serve: Any, tmp_path: Path) -> None:
        server = serve(catalog(FRESH_MODEL))
        manager = ModelManager(
            backend=RuntimeBackend.OLLAMA,
            settings=Settings(cache_dir=tmp_path, catalog_source="remote", registry_url=server.url),
        )

        assert isinstance(manager._registry_port, RemoteRegistry)
        assert "brand-new-model" in [s.name for s in manager.search("brand-new")]

    def test_remote_source_without_a_url_is_a_config_error(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError):
            ModelManager(
                backend=RuntimeBackend.OLLAMA,
                settings=Settings(cache_dir=tmp_path, catalog_source="remote"),
            )

    def test_auto_merges_the_remote_catalog_when_a_url_is_set(
        self, serve: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A configured registry_url must actually reach discovery under "auto"."""
        # Force the live Ollama catalog to fail so the base is the bundled one.
        monkeypatch.setattr(
            "modeldock.adapters.registry.ollama_library.OllamaLibraryRegistry._fetch_from_network",
            lambda self: None,
        )
        server = serve(catalog(FRESH_MODEL))
        manager = ModelManager(
            backend=RuntimeBackend.OLLAMA,
            settings=Settings(cache_dir=tmp_path, catalog_source="auto", registry_url=server.url),
        )

        assert isinstance(manager._registry_port, CompositeRegistry)
        names = {s.name for s in manager.list()}
        assert "brand-new-model" in names
        assert "llama3" in names

    def test_auto_without_a_url_keeps_the_previous_behaviour(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "modeldock.adapters.registry.ollama_library.OllamaLibraryRegistry._fetch_from_network",
            lambda self: None,
        )
        manager = ModelManager(backend=RuntimeBackend.OLLAMA, settings=Settings(cache_dir=tmp_path))

        assert isinstance(manager._registry_port, BundledRegistry)

    def test_sources_lists_the_remote_catalog_once(self, serve: Any, tmp_path: Path) -> None:
        server = serve(catalog(FRESH_MODEL))
        manager = ModelManager(
            backend=RuntimeBackend.OLLAMA,
            settings=Settings(cache_dir=tmp_path, catalog_source="remote", registry_url=server.url),
        )

        names = [info.name for info in manager.sources()]
        assert names.count(REMOTE) == 1
        assert names.count(BUNDLED) == 1

    def test_manager_refresh_reaches_the_remote_source(self, serve: Any, tmp_path: Path) -> None:
        server = serve(catalog(FRESH_MODEL))
        manager = ModelManager(
            backend=RuntimeBackend.OLLAMA,
            settings=Settings(cache_dir=tmp_path, catalog_source="remote", registry_url=server.url),
        )
        assert server.hits == 1

        manager.refresh_sources()

        assert server.hits == 2


def test_invalid_catalog_source_still_rejected() -> None:
    """Adding "remote" must not turn the allow-list into anything-goes."""
    with pytest.raises(ConfigError):
        Settings(catalog_source="nonsense")


def test_optional_remote_never_breaks_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed registry_url degrades under "auto" rather than raising."""
    monkeypatch.setattr(
        "modeldock.adapters.registry.ollama_library.OllamaLibraryRegistry._fetch_from_network",
        lambda self: None,
    )
    manager = ModelManager(
        backend=RuntimeBackend.OLLAMA,
        settings=Settings(cache_dir=tmp_path, registry_url="file:///etc/passwd"),
    )

    assert "llama3" in [s.name for s in manager.list()]


def test_registry_port_contract_is_satisfied(serve: Any, tmp_path: Path) -> None:
    from modeldock.ports.registry import RegistryPort

    server = serve(catalog(FRESH_MODEL))
    assert isinstance(RemoteRegistry(server.url, cache_dir=tmp_path), RegistryPort)
