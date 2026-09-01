"""Unit tests for GPT4All local model discovery (issue #30)."""

from __future__ import annotations

from pathlib import Path

from modeldock.adapters.runtimes.gpt4all import Gpt4AllRuntime
from modeldock.adapters.runtimes.registry import RuntimeRegistry
from modeldock.domain.model import RuntimeBackend


def test_list_installed_registers_supported_model_files(tmp_path: Path) -> None:
    (tmp_path / "Phi-3-mini.Q4_0.gguf").touch()
    (tmp_path / "legacy-model.bin").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "ignored.gguf").touch()

    runtime = Gpt4AllRuntime(models_dir=tmp_path)

    assert runtime.is_available() is True
    assert [ref.name for ref in runtime.list_installed()] == [
        "Phi-3-mini.Q4_0",
        "legacy-model",
    ]


def test_missing_models_directory_is_unavailable_and_empty(tmp_path: Path) -> None:
    runtime = Gpt4AllRuntime(models_dir=tmp_path / "missing")

    assert runtime.is_available() is False
    assert runtime.list_installed() == []


def test_registry_forwards_gpt4all_models_dir(tmp_path: Path) -> None:
    runtime = RuntimeRegistry().get(RuntimeBackend.GPT4ALL, models_dir=tmp_path)

    assert isinstance(runtime, Gpt4AllRuntime)
    assert runtime._models_dir == tmp_path
