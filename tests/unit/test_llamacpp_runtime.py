"""Unit tests for the llama.cpp runtime adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from modeldock.adapters.runtimes.llamacpp import LlamaCppRuntime
from modeldock.common.errors import DownloadError, ModelNotInstalledError, RuntimeUnavailableError
from modeldock.domain.model import Device, ModelRef, RuntimeBackend, RuntimeStatus


class _MockHTTPResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        return self._json_data


class _MockHTTPClient:
    """Mock httpx.Client for testing llama-server HTTP calls."""

    def __init__(
        self,
        health_status: int = 200,
        models_response: Dict[str, Any] | None = None,
    ) -> None:
        self._health_status = health_status
        self._models_response = models_response or {"data": []}
        self.get_calls: List[str] = []

    def get(self, url: str) -> _MockHTTPResponse:
        self.get_calls.append(url)
        if url == "/health":
            return _MockHTTPResponse(self._health_status, {"status": "ok"})
        if url == "/v1/models":
            return _MockHTTPResponse(200, self._models_response)
        return _MockHTTPResponse(404, {})


class _MockOpenAIClient:
    """Mock OpenAI client for testing chat completions."""

    def __init__(self) -> None:
        self.created_completions: List[Dict[str, Any]] = []

    @property
    def chat(self) -> Any:
        return self

    @property
    def completions(self) -> Any:
        return self

    def create(
        self, model: str, messages: List[Dict[str, str]], stream: bool = False, **opts: Any
    ) -> Any:
        self.created_completions.append({"model": model, "messages": messages})
        if stream:
            return self._stream_response()
        return self._single_response()

    def _stream_response(self) -> Any:
        class _StreamChunk:
            def __init__(self, content: str) -> None:
                self.choices = [Mock(delta=Mock(content=content))]

        def _gen():
            yield _StreamChunk("Hello")
            yield _StreamChunk(" world")

        return _gen()

    def _single_response(self) -> Any:
        response = Mock()
        response.choices = [Mock(message=Mock(content="Hello world"))]
        return response


def _runtime_with_http_client(http_client: _MockHTTPClient) -> LlamaCppRuntime:
    """Create a LlamaCppRuntime with a mock HTTP client."""
    runtime = LlamaCppRuntime()
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]
    return runtime


def _runtime_with_openai_client(openai_client: _MockOpenAIClient) -> LlamaCppRuntime:
    """Create a LlamaCppRuntime with a mock OpenAI client."""
    runtime = LlamaCppRuntime()
    runtime._client = openai_client
    return runtime


# --- Availability tests -----------------------------------------------------


def test_check_available_true_when_server_healthy() -> None:
    http_client = _MockHTTPClient(health_status=200)
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is True
    assert "/health" in http_client.get_calls


def test_check_available_false_when_server_down() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is False


def test_check_available_false_when_non_200_response() -> None:
    http_client = _MockHTTPClient(health_status=503)
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is False


def test_is_available_uses_check_available() -> None:
    http_client = _MockHTTPClient(health_status=200)
    runtime = _runtime_with_http_client(http_client)
    assert runtime.is_available() is True
    assert runtime.is_available() is True
    # Only one GET call to /health -- second call is served from cache.
    assert http_client.get_calls.count("/health") == 1


# --- list_installed tests ----------------------------------------------------


def test_list_installed_parses_the_loaded_model() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = _runtime_with_http_client(http_client)

    refs = runtime.list_installed()

    assert len(refs) == 1
    assert refs[0].name == "qwen2.5-7b-instruct"
    assert refs[0].tag == "latest"
    assert refs[0].backend == RuntimeBackend.LLAMACPP


def test_list_installed_round_trips_with_model_ref_parse() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = _runtime_with_http_client(http_client)

    assert runtime.is_installed(ModelRef.parse("qwen2.5-7b-instruct"))
    assert not runtime.is_installed(ModelRef.parse("other-model"))


def test_list_installed_returns_empty_when_server_unreachable() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


def test_list_installed_returns_empty_on_non_200() -> None:
    http_client = _MockHTTPClient()
    http_client.get = lambda url: _MockHTTPResponse(500, {})  # type: ignore[assignment]
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


def test_list_installed_handles_empty_models() -> None:
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


def test_list_installed_ignores_entries_without_an_id() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{}]})
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


# --- is_installed tests -------------------------------------------------------


def test_is_installed_true_when_model_loaded() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)
    assert runtime.is_installed(ref) is True


def test_is_installed_false_when_model_absent() -> None:
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)
    assert runtime.is_installed(ref) is False


# --- pull tests ----------------------------------------------------------------


def test_pull_skips_when_already_loaded() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)

    result = runtime.pull(ref)

    assert result.success is True
    assert result.already_present is True


def test_pull_fails_with_actionable_message_when_not_loaded() -> None:
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)

    result = runtime.pull(ref)

    assert result.success is False
    assert "llama.cpp does not support remote pull" in result.error
    assert "llama-server -m" in result.error


def test_pull_raises_when_server_unreachable() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)

    with pytest.raises(RuntimeUnavailableError):
        runtime.pull(ref)


def test_pull_reports_progress_lifecycle() -> None:
    class _Progress:
        def __init__(self) -> None:
            self.events: List[str] = []

        def start(self, total: int, desc: str = "") -> None:
            self.events.append(f"start:{total}")

        def finish(self, desc: str = "") -> None:
            self.events.append("finish")

    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)
    progress = _Progress()

    result = runtime.pull(ref, progress=progress)

    assert result.success is False
    assert "start:0" in progress.events
    assert "finish" in progress.events


# --- remove tests ----------------------------------------------------------------


def test_remove_raises_single_model_hint() -> None:
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)

    with pytest.raises(DownloadError) as exc_info:
        runtime.remove(ref)
    assert "llama-server -m" in str(exc_info.value)


def test_remove_fails_for_cloud_model() -> None:
    http_client = _MockHTTPClient()
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="glm-5.2", tag="cloud", backend=RuntimeBackend.LLAMACPP)

    with pytest.raises(DownloadError):
        runtime.remove(ref)


def test_remove_raises_runtime_unavailable_when_server_down() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP)

    with pytest.raises(RuntimeUnavailableError) as exc_info:
        runtime.remove(ref)
    assert "llama-server -m" in str(exc_info.value)


# --- run tests ----------------------------------------------------------------


def test_run_single_prompt_streams_tokens() -> None:
    openai_client = _MockOpenAIClient()
    runtime = _runtime_with_openai_client(openai_client)
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    written: List[str] = []
    with patch.object(LlamaCppRuntime, "_write", staticmethod(lambda t: written.append(t))):
        result = runtime.run(
            ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP),
            prompt="hi",
        )

    assert result.success is True
    assert result.completion_tokens == 2
    assert "".join(written) == "Hello world\n"


def test_run_raises_runtime_unavailable_when_server_down() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)

    with pytest.raises(RuntimeUnavailableError) as exc_info:
        runtime.run(
            ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP),
            prompt="hi",
        )
    assert "llama-server -m" in str(exc_info.value)


def test_run_raises_when_model_not_loaded() -> None:
    openai_client = _MockOpenAIClient()
    runtime = _runtime_with_openai_client(openai_client)
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    with pytest.raises(ModelNotInstalledError):
        runtime.run(
            ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP),
            prompt="hi",
        )


def test_run_single_prompt_wraps_sdk_error() -> None:
    class _BoomClient:
        @property
        def chat(self) -> Any:
            return self

        @property
        def completions(self) -> Any:
            return self

        def create(self, **opts: Any) -> Any:
            raise RuntimeError("boom")

    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime = LlamaCppRuntime()
    runtime._client = _BoomClient()
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    result = runtime.run(
        ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP),
        prompt="hi",
    )

    assert result.success is False
    assert "boom" in result.error


def test_run_repl_reads_stdin_until_exit() -> None:
    openai_client = _MockOpenAIClient()
    runtime = _runtime_with_openai_client(openai_client)
    http_client = _MockHTTPClient(models_response={"data": [{"id": "qwen2.5-7b-instruct"}]})
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    written: List[str] = []
    with (
        patch.object(LlamaCppRuntime, "_write", staticmethod(lambda t: written.append(t))),
        patch("sys.stdin", __import__("io").StringIO("first\nsecond\nexit\n")),
    ):
        result = runtime.run(
            ModelRef(name="qwen2.5-7b-instruct", tag="latest", backend=RuntimeBackend.LLAMACPP),
        )

    assert result.success is True
    assert result.completion_tokens == 4


# --- status tests ----------------------------------------------------------------


def test_status_reports_available_when_server_healthy() -> None:
    http_client = _MockHTTPClient(health_status=200)
    runtime = _runtime_with_http_client(http_client)

    status = runtime.status()

    assert isinstance(status, RuntimeStatus)
    assert status.available is True
    assert status.device == Device.UNKNOWN


def test_status_reports_unavailable_when_server_down() -> None:
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)

    status = runtime.status()

    assert status.available is False
    assert status.device == Device.UNKNOWN


# --- host configuration tests ------------------------------------------------


def test_host_override_applied() -> None:
    runtime = LlamaCppRuntime(host="http://custom-host:9999")
    assert runtime._resolve_host() == "http://custom-host:9999"


def test_env_host_used_when_no_explicit_host() -> None:
    import os

    os.environ["LLAMACPP_HOST"] = "http://envhost:8888"
    try:
        runtime = LlamaCppRuntime()
        assert runtime._resolve_host() == "http://envhost:8888"
    finally:
        del os.environ["LLAMACPP_HOST"]


def test_modeldock_env_wins_over_vendor_env() -> None:
    import os

    os.environ["MODELDOCK_LLAMACPP_HOST"] = "http://modeldock:8080"
    os.environ["LLAMACPP_HOST"] = "http://vendor:8080"
    try:
        runtime = LlamaCppRuntime()
        assert runtime._resolve_host() == "http://modeldock:8080"
    finally:
        del os.environ["MODELDOCK_LLAMACPP_HOST"]
        del os.environ["LLAMACPP_HOST"]


def test_default_host_used_when_no_override() -> None:
    import os

    os.environ.pop("MODELDOCK_LLAMACPP_HOST", None)
    os.environ.pop("LLAMACPP_HOST", None)
    runtime = LlamaCppRuntime()
    assert runtime._resolve_host() == "http://localhost:8080"


# --- API key tests -------------------------------------------------------------


def test_api_key_override_applied() -> None:
    runtime = LlamaCppRuntime(api_key="test-key-123")
    assert runtime._resolve_api_key() == "test-key-123"


def test_env_api_key_used_when_no_explicit_key() -> None:
    import os

    os.environ["LLAMACPP_API_KEY"] = "env-token-456"
    try:
        runtime = LlamaCppRuntime()
        assert runtime._resolve_api_key() == "env-token-456"
    finally:
        del os.environ["LLAMACPP_API_KEY"]


def test_default_api_key_used_when_no_override() -> None:
    import os

    os.environ.pop("LLAMACPP_API_KEY", None)
    runtime = LlamaCppRuntime()
    assert runtime._resolve_api_key() is None


# --- default_tag_for tests ------------------------------------------------------


def test_default_tag_for_returns_spec_default() -> None:
    from modeldock.domain.model import Category, ModelSpec

    runtime = LlamaCppRuntime()
    spec = ModelSpec(
        name="qwen",
        category=Category.CHAT,
        default_tag="qwen2.5-7b-instruct",
    )
    assert runtime.default_tag_for(spec) == "qwen2.5-7b-instruct"


# --- model suggestions (live Hugging Face catalog) --------------------------------
#
# llama.cpp has no catalog of its own; models_for_category/_capability resolve
# through the live Hugging Face GGUF listing (huggingface_catalog.py). These
# tests mock the network so they stay fast and deterministic.


def test_models_for_category_empty_when_hub_unreachable(tmp_path: Path) -> None:
    """No catalog of its own and no cache yet: an empty list, not a crash or a
    bogus Ollama-named suggestion.
    """
    from modeldock.domain.model import Capability, Category

    with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("network disabled for test")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_client

        runtime = LlamaCppRuntime(cache_dir=tmp_path)
        assert runtime.models_for_category(Category.CODING) == []
        assert runtime.models_for_capability(Capability.CHAT) == []


def test_models_for_category_uses_live_hub_catalog(tmp_path: Path) -> None:
    from modeldock.domain.model import Category

    with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "unit-test-org/Coder-7B-GGUF",
                "pipeline_tag": "text-generation",
                "tags": ["gguf", "conversational"],
            }
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_client

        runtime = LlamaCppRuntime(cache_dir=tmp_path)
        refs = runtime.models_for_category(Category.CODING)

    assert len(refs) == 1
    assert refs[0].name == "unit-test-org/Coder-7B-GGUF"
    assert refs[0].backend is RuntimeBackend.LLAMACPP


def test_models_for_capability_uses_live_hub_catalog(tmp_path: Path) -> None:
    from modeldock.domain.model import Capability

    with patch("modeldock.adapters.registry.huggingface_catalog.create_client") as mock_factory:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "unit-test-org/Embed-Model-GGUF",
                "pipeline_tag": "feature-extraction",
                "tags": ["gguf", "feature-extraction"],
            }
        ]
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_factory.return_value = mock_client

        runtime = LlamaCppRuntime(cache_dir=tmp_path)
        refs = runtime.models_for_capability(Capability.EMBED)

    assert len(refs) == 1
    assert refs[0].name == "unit-test-org/Embed-Model-GGUF"


# --- registry wiring --------------------------------------------------------------


def test_registered_as_builtin_backend() -> None:
    from modeldock.adapters.runtimes.registry import RuntimeRegistry

    registry = RuntimeRegistry()
    runtime = registry.get(RuntimeBackend.LLAMACPP)
    assert isinstance(runtime, LlamaCppRuntime)
    assert runtime.backend == RuntimeBackend.LLAMACPP
