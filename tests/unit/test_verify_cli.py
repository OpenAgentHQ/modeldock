"""Unit tests: verify command — exit codes, --all behavior, JSON output."""

from __future__ import annotations

from typing import Any, Optional

import pytest
from typer.testing import CliRunner

import modeldock.cli.factory as factory
from modeldock.cli.app import app
from modeldock.domain.model import ModelRef

runner = CliRunner()


class _VerifyManager:
    """Stub manager: installed() returns configured refs, verify() looks up results."""

    def __init__(
        self,
        installed_refs: Optional[list[ModelRef]] = None,
        verify_results: Optional[dict[str, bool]] = None,
        **_: Any,
    ) -> None:
        self._installed_refs = installed_refs or []
        self._verify_results = verify_results or {}

    def installed(self) -> list[ModelRef]:
        return self._installed_refs

    def verify(self, name: str) -> bool:
        return self._verify_results.get(name, True)


# ---------------------------------------------------------------------------
# --all
# ---------------------------------------------------------------------------


def test_verify_all_all_pass_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    refs = [ModelRef.parse("llama3"), ModelRef.parse("qwen3")]
    mgr = _VerifyManager(installed_refs=refs, verify_results={"llama3": True, "qwen3": True})
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "--all"])
    assert result.exit_code == 0


def test_verify_all_one_fails_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    refs = [ModelRef.parse("llama3"), ModelRef.parse("qwen3")]
    mgr = _VerifyManager(installed_refs=refs, verify_results={"llama3": True, "qwen3": False})
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "--all"])
    assert result.exit_code == 1


def test_verify_all_empty_installed_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = _VerifyManager(installed_refs=[])
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "--all"])
    assert result.exit_code == 0


def test_verify_all_with_explicit_models_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """--all combined with explicit model names is invalid, not silently merged."""
    mgr = _VerifyManager()
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "--all", "llama3"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# explicit model names
# ---------------------------------------------------------------------------


def test_verify_explicit_model_passes_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = _VerifyManager(verify_results={"llama3": True})
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "llama3"])
    assert result.exit_code == 0


def test_verify_explicit_model_fails_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = _VerifyManager(verify_results={"llama3": False})
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "llama3"])
    assert result.exit_code == 1


def test_verify_no_args_no_all_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = _VerifyManager()
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# --json
# ---------------------------------------------------------------------------


def test_verify_json_output_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = _VerifyManager(verify_results={"llama3": True})
    monkeypatch.setattr(factory, "ModelManager", lambda **kw: mgr)
    result = runner.invoke(app, ["verify", "llama3", "--json"])
    assert result.exit_code == 0
    assert '"name": "llama3"' in result.stdout
    assert '"ok": true' in result.stdout
