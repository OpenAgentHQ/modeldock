"""Integration tests against a real Ollama runtime.

These run only when Ollama is installed and reachable. They auto-skip
otherwise so CI stays green without a runtime (Development.md S6).
"""

from __future__ import annotations

import shutil

import pytest

from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.domain.model import ModelRef, RuntimeBackend

ollama_present = shutil.which("ollama") is not None
try:
    import ollama  # noqa: F401 - optional extra; required for these tests

    sdk_present = True
except ImportError:
    sdk_present = False

pytestmark = pytest.mark.integration


def _runtime() -> object:
    return RuntimeRegistry().get(RuntimeBackend.OLLAMA)


@pytest.mark.skipif(not ollama_present, reason="Ollama CLI not installed")
def test_ollama_runtime_available() -> None:
    runtime = _runtime()
    # is_available may be False if the daemon isn't running; we only assert the
    # call returns a bool without raising.
    assert isinstance(runtime.is_available(), bool)


@pytest.mark.skipif(
    not (ollama_present and sdk_present),
    reason="Ollama CLI and Python SDK not both available",
)
def test_ollama_list_installed_runs() -> None:
    runtime = _runtime()
    # Should not raise even if nothing is installed.
    assert isinstance(runtime.list_installed(), list)


@pytest.mark.skipif(not ollama_present, reason="Ollama CLI not installed")
def test_ollama_pull_and_remove() -> None:
    runtime = _runtime()
    if not runtime.is_available():
        pytest.skip("Ollama daemon not running")
    ref = ModelRef.parse("llama3:8b")
    result = runtime.pull(ref)
    assert result.success
    assert runtime.is_installed(ref)
    runtime.remove(ref)
    assert not runtime.is_installed(ref)
