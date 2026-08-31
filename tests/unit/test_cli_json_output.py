"""Unit tests for machine-readable CLI output (``--json``).

Covers issue #40: ``list``, ``info``, ``installed``, ``search`` and ``runtimes``
must emit parseable JSON on stdout, errors must emit a JSON object on stderr,
and the human output must be unchanged when the flag is absent.

Every test injects a stub manager so no real runtime or network is needed.
"""

from __future__ import annotations

import json
from typing import Any, List

import pytest
from typer.testing import CliRunner

import modeldock.cli.commands.info as info_cmd_mod
import modeldock.cli.commands.installed as installed_cmd_mod
import modeldock.cli.commands.list as list_cmd_mod
import modeldock.cli.commands.runtimes as runtimes_cmd_mod
import modeldock.cli.commands.search as search_cmd_mod
from modeldock.cli.app import app
from modeldock.cli.console import to_jsonable
from modeldock.common.errors import ModelNotFoundError
from modeldock.domain.model import (
    Capability,
    Category,
    Device,
    ModelInfo,
    ModelRef,
    ModelSpec,
    ModelVariant,
    RuntimeBackend,
    RuntimeStatus,
)
from modeldock.domain.source import OLLAMA_OFFICIAL


def _make_runner() -> CliRunner:
    """Build a runner that keeps stdout and stderr separate.

    Older Typer/Click needs an explicit ``mix_stderr=False``; newer versions
    dropped the argument and split the streams by default.
    """
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


# stderr must stay separate so the JSON error object can be asserted on its own.
runner = _make_runner()

_SPEC = ModelSpec(
    name="llama3",
    aliases=["llama"],
    category=Category.CHAT,
    capabilities=[Capability.CHAT, Capability.TOOL_USE],
    default_tag="8b",
    variants=[ModelVariant(tag="8b", params="8B", size_bytes=4_700_000_000)],
    description="Meta Llama 3",
    source=OLLAMA_OFFICIAL,
)

_INFO = ModelInfo.from_spec(_SPEC, installed_tags=["8b"])

_REFS = [ModelRef(name="llama3", tag="8b", backend=RuntimeBackend.OLLAMA)]

_STATUSES = [
    RuntimeStatus(
        backend=RuntimeBackend.OLLAMA,
        available=True,
        device=Device.GPU,
        loaded_models=["llama3:8b"],
    ),
    RuntimeStatus(backend=RuntimeBackend.VLLM, available=False, device=Device.UNKNOWN),
]


class _StubManager:
    """Manager stub returning fixed discovery data."""

    def __init__(self, **_: Any) -> None:
        pass

    def list(self) -> List[ModelSpec]:
        return [_SPEC]

    def search(self, query: str) -> List[ModelSpec]:
        return [_SPEC]

    def installed(self) -> List[ModelRef]:
        return list(_REFS)

    def info(self, name: str) -> ModelInfo:
        return _INFO

    def runtimes(self) -> List[RuntimeStatus]:
        return list(_STATUSES)


class _RaisingManager:
    """Manager stub whose every discovery call fails."""

    def __init__(self, **_: Any) -> None:
        pass

    def _fail(self) -> Any:
        raise ModelNotFoundError("nope")

    def list(self) -> Any:
        return self._fail()

    def search(self, query: str) -> Any:
        return self._fail()

    def installed(self) -> Any:
        return self._fail()

    def info(self, name: str) -> Any:
        return self._fail()

    def runtimes(self) -> Any:
        return self._fail()


_COMMAND_MODULES = (
    list_cmd_mod,
    search_cmd_mod,
    installed_cmd_mod,
    info_cmd_mod,
    runtimes_cmd_mod,
)

_ARGV = {
    "list": ["list"],
    "search": ["search", "chat"],
    "installed": ["installed"],
    "info": ["info", "llama3"],
    "runtimes": ["runtimes"],
}


@pytest.fixture()
def stub_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in _COMMAND_MODULES:
        monkeypatch.setattr(module, "ModelManager", _StubManager)


@pytest.fixture()
def raising_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in _COMMAND_MODULES:
        monkeypatch.setattr(module, "ModelManager", _RaisingManager)


# --- to_jsonable -----------------------------------------------------------


def test_to_jsonable_passes_through_primitives() -> None:
    assert to_jsonable(None) is None
    assert to_jsonable(True) is True
    assert to_jsonable(3) == 3
    assert to_jsonable(1.5) == 1.5
    assert to_jsonable("x") == "x"


def test_to_jsonable_unwraps_str_enums_to_their_value() -> None:
    # Capability/Category/RuntimeBackend subclass str; the enum branch must win
    # so we emit "chat", never the member repr.
    assert to_jsonable(Category.CHAT) == "chat"
    assert to_jsonable(Capability.TOOL_USE) == "tool_use"
    assert to_jsonable(RuntimeBackend.LM_STUDIO) == "lmstudio"


def test_to_jsonable_dumps_pydantic_models() -> None:
    dumped = to_jsonable(_SPEC)
    assert dumped["name"] == "llama3"
    assert dumped["category"] == "chat"
    assert dumped["capabilities"] == ["chat", "tool_use"]


def test_to_jsonable_recurses_into_containers() -> None:
    assert to_jsonable([Category.CHAT, Category.CODING]) == ["chat", "coding"]
    assert to_jsonable((1, "a")) == [1, "a"]
    assert to_jsonable({Category.CHAT: [Capability.CHAT]}) == {"chat": ["chat"]}


def test_to_jsonable_falls_back_to_str_for_unknown_types() -> None:
    class _Opaque:
        def __str__(self) -> str:
            return "opaque"

    assert to_jsonable(_Opaque()) == "opaque"


def test_to_jsonable_output_is_serialisable() -> None:
    # The whole point: whatever comes back must survive json.dumps.
    json.dumps(to_jsonable([_SPEC, _INFO, *_REFS, *_STATUSES]))


# --- success paths ---------------------------------------------------------


@pytest.mark.parametrize("command", ["list", "search", "installed", "runtimes"])
def test_json_flag_emits_a_parseable_array(command: str, stub_manager: None) -> None:
    result = runner.invoke(app, [*_ARGV[command], "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload


def test_info_json_emits_a_single_object(stub_manager: None) -> None:
    result = runner.invoke(app, ["info", "llama3", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload["name"] == "llama3"
    assert payload["installed"] is True
    assert payload["installed_tags"] == ["8b"]


def test_list_json_carries_catalog_fields_as_primitives(stub_manager: None) -> None:
    payload = json.loads(runner.invoke(app, ["list", "--json"]).stdout)
    entry = payload[0]
    assert entry["name"] == "llama3"
    assert entry["category"] == "chat"
    assert entry["capabilities"] == ["chat", "tool_use"]
    assert entry["source"] == OLLAMA_OFFICIAL
    assert entry["variants"][0]["tag"] == "8b"


def test_installed_json_carries_ref_fields(stub_manager: None) -> None:
    payload = json.loads(runner.invoke(app, ["installed", "--json"]).stdout)
    assert payload == [{"name": "llama3", "tag": "8b", "backend": "ollama"}]


def test_runtimes_json_carries_status_fields(stub_manager: None) -> None:
    payload = json.loads(runner.invoke(app, ["runtimes", "--json"]).stdout)
    assert payload[0]["backend"] == "ollama"
    assert payload[0]["available"] is True
    assert payload[0]["device"] == "gpu"
    assert payload[0]["loaded_models"] == ["llama3:8b"]
    assert payload[1]["available"] is False
    assert payload[1]["device"] == "unknown"


def test_search_json_reflects_the_query_results(stub_manager: None) -> None:
    payload = json.loads(runner.invoke(app, ["search", "chat", "--json"]).stdout)
    assert [entry["name"] for entry in payload] == ["llama3"]


def test_json_output_has_no_stderr_noise(stub_manager: None) -> None:
    # A script piping stdout must not have to filter anything out of stderr.
    result = runner.invoke(app, ["list", "--json"])
    assert result.stderr == ""


# --- failure paths ---------------------------------------------------------


@pytest.mark.parametrize("command", ["list", "search", "installed", "info", "runtimes"])
def test_json_flag_emits_a_json_error_object_on_failure(
    command: str, raising_manager: None
) -> None:
    result = runner.invoke(app, [*_ARGV[command], "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "ModelNotFoundError"
    assert "nope" in payload["error"]["message"]


def test_failure_without_json_flag_stays_plain_text(raising_manager: None) -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert result.stderr.startswith("Error: ")


# --- human output is unchanged ---------------------------------------------


@pytest.mark.parametrize("command", ["list", "search", "installed", "runtimes"])
def test_without_json_flag_output_is_not_json(command: str, stub_manager: None) -> None:
    result = runner.invoke(app, _ARGV[command])
    assert result.exit_code == 0
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)


def test_info_without_json_flag_keeps_the_field_lines(stub_manager: None) -> None:
    result = runner.invoke(app, ["info", "llama3"])
    assert result.exit_code == 0
    assert "Name:" in result.stdout
    assert "Category:" in result.stdout
    assert "Installed:" in result.stdout


def test_runtimes_table_lists_every_backend(stub_manager: None) -> None:
    result = runner.invoke(app, ["runtimes"])
    assert result.exit_code == 0
    assert "ollama" in result.stdout
    assert "vllm" in result.stdout
