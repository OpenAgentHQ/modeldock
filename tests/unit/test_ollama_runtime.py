"""Unit tests for the Ollama runtime adapter."""

from __future__ import annotations

import time
from typing import Any

from modeldock.adapters.runtimes.ollama import OllamaRuntime
from modeldock.domain.model import ModelRef


class _PullClient:
    def __init__(self, list_responses: list[dict[str, Any]]) -> None:
        self._list_responses = iter(list_responses)
        self.list_calls = 0

    def pull(self, name: str, stream: bool = False) -> None:
        pass

    def list(self) -> dict[str, Any]:
        self.list_calls += 1
        return next(self._list_responses)


def test_pull_retries_until_model_is_listed(monkeypatch: Any) -> None:
    client = _PullClient(
        [
            {"models": []},
            {"models": [{"name": "llama3:latest"}]},
        ]
    )
    runtime = OllamaRuntime()
    runtime._client = client
    sleep_calls: list[float] = []
    monkeypatch.setattr(time, "sleep", sleep_calls.append)

    result = runtime._do_pull(ModelRef.parse("llama3"), progress=None)

    assert result.success
    assert client.list_calls == 2
    assert sleep_calls == [0.1]


def test_pull_fails_when_model_never_appears(monkeypatch: Any) -> None:
    client = _PullClient([{"models": []}, {"models": []}])
    runtime = OllamaRuntime()
    runtime._client = client
    monkeypatch.setattr(time, "sleep", lambda _: None)

    result = runtime._do_pull(ModelRef.parse("llama3"), progress=None)

    assert not result.success
    assert result.error == "llama3:latest not listed after pull"
    assert client.list_calls == 2
