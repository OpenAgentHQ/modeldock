"""Integration tests against a real Ollama runtime.

These run only when Ollama is installed and reachable. They auto-skip
otherwise so CI stays green without a runtime (Development.md S6).
"""

from __future__ import annotations

import shutil

import pytest

from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.domain.model import Device, ModelRef, RuntimeBackend, RuntimeStatus

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


@pytest.mark.skipif(
    not (ollama_present and sdk_present),
    reason="Ollama CLI and Python SDK not both available",
)
def test_ollama_status_device_detection() -> None:
    """status() reports a valid device and matches `ollama ps` (issue #11)."""
    import subprocess

    runtime = _runtime()
    if not runtime.is_available():
        pytest.skip("Ollama daemon not running")

    status = runtime.status()
    assert isinstance(status, RuntimeStatus)
    assert status.available is True
    assert status.device in (Device.GPU, Device.CPU, Device.UNKNOWN)

    # Load a small installed model so it becomes resident, then re-check.
    # Skip cloud/subscription models (tag contains "cloud") which can't run locally.
    installed = [r for r in runtime.list_installed() if "cloud" not in r.tag]
    if not installed:
        pytest.skip("No locally-runnable models installed to load")
    ref = installed[0]
    client = runtime._ensure_client()
    try:
        for _ in client.generate(ref.qualified_name(), prompt="ping", stream=True):
            pass
    except Exception:
        pytest.skip("Could not load a model for device detection")

    status = runtime.status()
    # Cross-check against `ollama ps` PROCESSOR column when available.
    try:
        out = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=10, check=True
        ).stdout
    except Exception:
        out = ""
    if ref.name in out and "CPU" in out:
        assert status.device is Device.CPU
    elif ref.name in out and "GPU" in out:
        assert status.device is Device.GPU
