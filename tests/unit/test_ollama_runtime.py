"""Unit tests for the Ollama runtime adapter."""

from __future__ import annotations

import time
from typing import Any, Iterator, List

import pytest

from modeldock.adapters.runtimes.ollama import OllamaRuntime
from modeldock.common.errors import DownloadError, RuntimeUnavailableError
from modeldock.domain.model import ModelRef


class _PullClient:
    """Fake ollama.Client for pull/streaming behavior."""

    def __init__(self, list_responses: List[dict[str, Any]]) -> None:
        self._list_responses = iter(list_responses)
        self.list_calls = 0
        self.pull_calls: List[str] = []
        self.deleted: List[str] = []

    def pull(self, name: str, stream: bool = False) -> Any:
        self.pull_calls.append(name)
        if stream:

            def _gen() -> Iterator[dict[str, Any]]:
                yield {"status": "pulling", "completed": 50, "total": 100}
                yield {"status": "success", "completed": 100, "total": 100}

            return _gen()
        return None

    def list(self) -> dict[str, Any]:
        self.list_calls += 1
        try:
            return next(self._list_responses)
        except StopIteration:
            return {"models": []}

    def delete(self, name: str) -> dict[str, Any]:
        self.deleted.append(name)
        return {"status": "success"}


def _runtime_with(client: Any) -> OllamaRuntime:
    runtime = OllamaRuntime()
    runtime._client = client
    return runtime


def test_pull_retries_until_model_is_listed(monkeypatch: Any) -> None:
    client = _PullClient(
        [
            {"models": []},
            {"models": [{"name": "llama3:latest"}]},
        ]
    )
    runtime = _runtime_with(client)
    sleep_calls: List[float] = []
    monkeypatch.setattr(time, "sleep", sleep_calls.append)

    result = runtime._do_pull(ModelRef.parse("llama3"), progress=None)

    assert result.success
    assert client.list_calls == 2
    assert sleep_calls == [0.1]


def test_pull_fails_when_model_never_appears(monkeypatch: Any) -> None:
    client = _PullClient([{"models": []}, {"models": []}])
    runtime = _runtime_with(client)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    result = runtime._do_pull(ModelRef.parse("llama3"), progress=None)

    assert not result.success
    assert result.error == "llama3:latest not listed after pull"
    assert client.list_calls == 10


def test_pull_streams_progress_and_accounts_bytes(monkeypatch: Any) -> None:
    client = _PullClient([{"models": [{"name": "llama3:latest"}]}])
    runtime = _runtime_with(client)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    events: List[str] = []

    class _Progress:
        def start(self, total: int, desc: str = "") -> None:
            events.append(f"start:{total}")

        def update(self, advance: int) -> None:
            events.append(f"update:{advance}")

        def finish(self, desc: str = "") -> None:
            events.append("finish")

    result = runtime._do_pull(ModelRef.parse("llama3"), progress=_Progress())

    assert result.success
    assert result.bytes_downloaded == 100
    assert "start:100" in events
    assert "update:50" in events
    assert "finish" in events


def test_list_installed_parses_model_field() -> None:
    client = _PullClient([{"models": [{"model": "llama3:latest"}, {"model": "qwen3:8b"}]}])
    runtime = _runtime_with(client)

    refs = runtime.list_installed()

    assert [r.qualified_name() for r in refs] == ["llama3:latest", "qwen3:8b"]
    assert all(r.backend.value == "ollama" for r in refs)


def test_list_installed_returns_empty_when_daemon_unreachable() -> None:
    class _DownClient:
        def list(self) -> dict[str, Any]:
            raise RuntimeError("connection refused")

    runtime = _runtime_with(_DownClient())
    # Daemon down is an expected offline state: degrade to an empty list.
    assert runtime.list_installed() == []


def test_list_installed_raises_when_sdk_missing() -> None:
    runtime = OllamaRuntime()

    def _boom() -> Any:
        raise RuntimeUnavailableError(
            "ollama", hint="Install the SDK with `pip install modeldock[ollama]`."
        )

    runtime._ensure_client = _boom  # type: ignore[assignment]
    with pytest.raises(RuntimeUnavailableError):
        runtime.list_installed()


def test_check_available_false_when_sdk_missing() -> None:
    runtime = OllamaRuntime()

    def _boom() -> Any:
        raise RuntimeUnavailableError(
            "ollama", hint="Install the SDK with `pip install modeldock[ollama]`."
        )

    runtime._ensure_client = _boom  # type: ignore[assignment]
    # is_available() is a boolean probe: SDK missing => unavailable, no raise.
    assert runtime.is_available() is False


def test_check_available_false_when_daemon_down() -> None:
    class _DownClient:
        def list(self) -> dict[str, Any]:
            raise RuntimeError("connection refused")

    runtime = _runtime_with(_DownClient())
    assert runtime.is_available() is False


def test_remove_deletes_and_wraps_errors() -> None:
    client = _PullClient([{"models": []}])
    runtime = _runtime_with(client)

    runtime.remove(ModelRef.parse("llama3:latest"))
    assert client.deleted == ["llama3:latest"]


def test_remove_wraps_sdk_error_as_download_error() -> None:
    class _FailClient:
        def delete(self, name: str) -> dict[str, Any]:
            raise RuntimeError("model not found")

    runtime = _runtime_with(_FailClient())
    with pytest.raises(DownloadError):
        runtime.remove(ModelRef.parse("llama3:latest"))


def test_host_override_applied_at_client_build(monkeypatch: Any) -> None:
    built: dict[str, Any] = {}

    class _FakeOllama:
        def Client(self, host: str, timeout: float = 30.0) -> Any:
            built["host"] = host
            built["timeout"] = timeout
            return _PullClient([{"models": []}])

    fake_mod = _FakeOllama()
    monkeypatch.setitem(__import__("sys").modules, "ollama", fake_mod)

    runtime = OllamaRuntime(host="http://example:1234")
    runtime.is_available()
    assert built["host"] == "http://example:1234"
    assert built["timeout"] == 30.0


def test_env_host_used_when_no_explicit_host(monkeypatch: Any) -> None:
    built: dict[str, Any] = {}

    class _FakeOllama:
        def Client(self, host: str, timeout: float = 30.0) -> Any:
            built["host"] = host
            return _PullClient([{"models": []}])

    monkeypatch.setitem(__import__("sys").modules, "ollama", _FakeOllama())
    monkeypatch.setenv("OLLAMA_HOST", "http://envhost:9999")

    runtime = OllamaRuntime()
    runtime.is_available()
    assert built["host"] == "http://envhost:9999"
