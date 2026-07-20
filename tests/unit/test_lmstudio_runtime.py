"""Unit tests for the LM Studio runtime adapter."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from modeldock.adapters.runtimes.lmstudio import LMStudioRuntime
from modeldock.common.errors import DownloadError, ModelNotInstalledError
from modeldock.domain.model import Device, ModelRef, RuntimeBackend, RuntimeStatus


class _MockHTTPResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        return self._json_data


class _MockHTTPClient:
    """Mock httpx.Client for testing LM Studio HTTP calls."""

    def __init__(
        self,
        models_response: Dict[str, Any] | None = None,
        download_response: Dict[str, Any] | None = None,
        unload_response: Dict[str, Any] | None = None,
    ) -> None:
        self._models_response = models_response or {"data": []}
        self._download_response = download_response or {"status": "completed"}
        self._unload_response = unload_response or {"status": "ok"}
        self.get_calls: List[str] = []
        self.post_calls: List[str] = []

    def get(self, url: str) -> _MockHTTPResponse:
        self.get_calls.append(url)
        if url == "/v1/models":
            return _MockHTTPResponse(200, self._models_response)
        elif url == "/api/v1/models/download/status":
            return _MockHTTPResponse(200, self._download_response)
        return _MockHTTPResponse(404, {})

    def post(self, url: str, json: Dict[str, Any] | None = None) -> _MockHTTPResponse:
        self.post_calls.append(url)
        if url == "/api/v1/models/download":
            return _MockHTTPResponse(200, self._download_response)
        elif url == "/api/v1/models/unload":
            return _MockHTTPResponse(200, self._unload_response)
        return _MockHTTPResponse(404, {})


class _MockOpenAIClient:
    """Mock OpenAI client for testing chat completions."""

    def __init__(self, installed: bool = True) -> None:
        self._installed = installed
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
        """Return a mock streaming response."""

        class _StreamChunk:
            def __init__(self, content: str) -> None:
                self.choices = [Mock(delta=Mock(content=content))]

        def _gen():
            yield _StreamChunk("Hello")
            yield _StreamChunk(" world")

        return _gen()

    def _single_response(self) -> Any:
        """Return a mock single response."""
        response = Mock()
        response.choices = [Mock(message=Mock(content="Hello world"))]
        return response


def _runtime_with_http_client(http_client: _MockHTTPClient) -> LMStudioRuntime:
    """Create a LMStudioRuntime with a mock HTTP client."""
    runtime = LMStudioRuntime()
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]
    return runtime


def _runtime_with_openai_client(openai_client: _MockOpenAIClient) -> LMStudioRuntime:
    """Create a LMStudioRuntime with a mock OpenAI client."""
    runtime = LMStudioRuntime()
    runtime._client = openai_client
    return runtime


# --- Availability tests ---------------------------------------------------


def test_check_available_true_when_server_running() -> None:
    """Test _check_available returns True when server is reachable."""
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is True
    assert "/v1/models" in http_client.get_calls


def test_check_available_false_when_server_down() -> None:
    """Test _check_available returns False when server is unreachable."""
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is False


def test_check_available_false_when_non_200_response() -> None:
    """Test _check_available returns False on non-200 response."""
    http_client = _MockHTTPClient()
    http_client.get = lambda url: _MockHTTPResponse(500, {})  # type: ignore[assignment]
    runtime = _runtime_with_http_client(http_client)
    assert runtime._check_available() is False


def test_is_available_uses_check_available() -> None:
    """Test is_available() delegates to _check_available with caching."""
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    # First call checks availability
    assert runtime.is_available() is True
    # Second call uses cache (no additional HTTP call)
    assert runtime.is_available() is True
    # Only one GET call to /v1/models
    assert http_client.get_calls.count("/v1/models") == 1


# --- list_installed tests -------------------------------------------------


def test_list_installed_parses_models() -> None:
    """Test list_installed parses model IDs correctly."""
    http_client = _MockHTTPClient(
        models_response={
            "data": [
                {"id": "qwen/qwen3.5-9b"},
                {"id": "llama/llama-3.1-8b"},
                {"id": "deepseek-r1-distill-qwen-7b"},
            ]
        }
    )
    runtime = _runtime_with_http_client(http_client)

    refs = runtime.list_installed()

    assert len(refs) == 3
    assert refs[0].name == "qwen"
    assert refs[0].tag == "qwen3.5-9b"
    assert refs[1].name == "llama"
    assert refs[1].tag == "llama-3.1-8b"
    assert refs[2].name == "deepseek-r1-distill-qwen-7b"
    assert refs[2].tag == "latest"
    assert all(r.backend.value == "lmstudio" for r in refs)


def test_list_installed_returns_empty_when_server_unreachable() -> None:
    """Test list_installed returns empty list when server is down."""
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


def test_list_installed_returns_empty_on_non_200() -> None:
    """Test list_installed returns empty list on API error."""
    http_client = _MockHTTPClient()
    http_client.get = lambda url: _MockHTTPResponse(500, {})  # type: ignore[assignment]
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


def test_list_installed_handles_empty_models() -> None:
    """Test list_installed handles empty model list."""
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    assert runtime.list_installed() == []


# --- is_installed tests ---------------------------------------------------


def test_is_installed_true_when_model_present() -> None:
    """Test is_installed returns True when model is in list."""
    http_client = _MockHTTPClient(
        models_response={"data": [{"id": "qwen/qwen3.5-9b"}]}
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)
    assert runtime.is_installed(ref) is True


def test_is_installed_false_when_model_absent() -> None:
    """Test is_installed returns False when model is not in list."""
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)
    assert runtime.is_installed(ref) is False


# --- pull tests -----------------------------------------------------------


def test_pull_skips_when_already_installed() -> None:
    """Test pull is idempotent when model is already installed."""
    http_client = _MockHTTPClient(
        models_response={"data": [{"id": "qwen/qwen3.5-9b"}]}
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    result = runtime.pull(ref)

    assert result.success is True
    assert result.already_present is True
    # No download API calls
    assert http_client.post_calls == []


def test_pull_downloads_when_not_installed() -> None:
    """Test pull downloads model when not installed."""
    http_client = _MockHTTPClient(
        models_response={"data": []},
        download_response={"status": "completed"},
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    result = runtime.pull(ref)

    assert result.success is True
    assert "/api/v1/models/download" in http_client.post_calls


def test_pull_fails_when_download_api_unavailable() -> None:
    """Test pull fails when download API returns error."""
    http_client = _MockHTTPClient(
        models_response={"data": []},
        download_response={"status": "failed", "error": "Model not found"},
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    result = runtime.pull(ref)

    assert result.success is False
    assert "Download failed" in result.error


def test_pull_fails_when_network_error() -> None:
    """Test pull fails gracefully on network error."""
    http_client = MagicMock()
    http_client.get.return_value = _MockHTTPResponse(200, {"data": []})
    http_client.post.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    result = runtime.pull(ref)

    assert result.success is False
    assert "Download failed" in result.error


def test_pull_reports_progress() -> None:
    """Test pull reports progress correctly."""

    class _Progress:
        def __init__(self) -> None:
            self.events: List[str] = []

        def start(self, total: int, desc: str = "") -> None:
            self.events.append(f"start:{total}")

        def finish(self, desc: str = "") -> None:
            self.events.append("finish")

    http_client = _MockHTTPClient(
        models_response={"data": []},
        download_response={"status": "completed"},
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)
    progress = _Progress()

    result = runtime.pull(ref, progress=progress)

    assert result.success is True
    assert "start:0" in progress.events
    assert "finish" in progress.events


# --- remove tests ---------------------------------------------------------


def test_remove_unloads_model() -> None:
    """Test remove unloads model via API."""
    http_client = _MockHTTPClient(
        unload_response={"status": "ok"},
    )
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    runtime.remove(ref)

    assert "/api/v1/models/unload" in http_client.post_calls


def test_remove_fails_for_cloud_model() -> None:
    """Test remove fails fast for cloud models."""
    http_client = _MockHTTPClient()
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="glm-5.2", tag="cloud", backend=RuntimeBackend.LM_STUDIO)

    with pytest.raises(DownloadError):
        runtime.remove(ref)
    # No API calls for cloud models
    assert http_client.post_calls == []


def test_remove_suggests_ui_when_unload_fails() -> None:
    """Test remove suggests using UI when unload fails."""
    http_client = MagicMock()
    http_client.get.return_value = _MockHTTPResponse(200, {"data": []})
    http_client.post.side_effect = RuntimeError("unload failed")
    runtime = _runtime_with_http_client(http_client)
    ref = ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO)

    with pytest.raises(DownloadError) as exc_info:
        runtime.remove(ref)
    assert "LM Studio's UI" in str(exc_info.value)


# --- run tests ------------------------------------------------------------


def test_run_single_prompt_streams_tokens() -> None:
    """Test run with single prompt streams tokens to stdout."""
    openai_client = _MockOpenAIClient(installed=True)
    runtime = _runtime_with_openai_client(openai_client)
    # Add model to installed list
    http_client = _MockHTTPClient(
        models_response={"data": [{"id": "qwen/qwen3.5-9b"}]}
    )
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    written: List[str] = []
    with patch.object(LMStudioRuntime, "_write", staticmethod(lambda t: written.append(t))):
        result = runtime.run(
            ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO),
            prompt="hi",
        )

    assert result.success is True
    assert result.completion_tokens == 2
    assert "".join(written) == "Hello world\n"


def test_run_raises_when_model_not_installed() -> None:
    """Test run raises error when model is not installed."""
    openai_client = _MockOpenAIClient(installed=False)
    runtime = _runtime_with_openai_client(openai_client)
    # Empty model list
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    with pytest.raises(ModelNotInstalledError):
        runtime.run(
            ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO),
            prompt="hi",
        )


def test_run_single_prompt_wraps_sdk_error() -> None:
    """Test run wraps SDK errors as RunResult."""

    class _BoomClient:
        @property
        def chat(self) -> Any:
            return self

        @property
        def completions(self) -> Any:
            return self

        def create(self, **opts: Any) -> Any:
            raise RuntimeError("boom")

    http_client = _MockHTTPClient(
        models_response={"data": [{"id": "qwen/qwen3.5-9b"}]}
    )
    runtime = LMStudioRuntime()
    runtime._client = _BoomClient()
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    result = runtime.run(
        ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO),
        prompt="hi",
    )

    assert result.success is False
    assert "boom" in result.error


def test_run_repl_reads_stdin_until_exit() -> None:
    """Test run REPL mode reads stdin until exit command."""
    openai_client = _MockOpenAIClient(installed=True)
    runtime = _runtime_with_openai_client(openai_client)
    http_client = _MockHTTPClient(
        models_response={"data": [{"id": "qwen/qwen3.5-9b"}]}
    )
    runtime._ensure_http_client = lambda: http_client  # type: ignore[assignment]

    written: List[str] = []
    with patch.object(LMStudioRuntime, "_write", staticmethod(lambda t: written.append(t))), \
         patch("sys.stdin", __import__("io").StringIO("first\nsecond\nexit\n")):
        result = runtime.run(
            ModelRef(name="qwen", tag="qwen3.5-9b", backend=RuntimeBackend.LM_STUDIO),
        )

    assert result.success is True
    assert result.completion_tokens == 4


# --- status tests ---------------------------------------------------------


def test_status_reports_available_when_server_running() -> None:
    """Test status reports available when server is running."""
    http_client = _MockHTTPClient(models_response={"data": []})
    runtime = _runtime_with_http_client(http_client)

    status = runtime.status()

    assert isinstance(status, RuntimeStatus)
    assert status.available is True
    assert status.device == Device.UNKNOWN


def test_status_reports_unavailable_when_server_down() -> None:
    """Test status reports unavailable when server is down."""
    http_client = MagicMock()
    http_client.get.side_effect = RuntimeError("connection refused")
    runtime = _runtime_with_http_client(http_client)

    status = runtime.status()

    assert status.available is False
    assert status.device == Device.UNKNOWN


# --- host configuration tests ---------------------------------------------


def test_host_override_applied() -> None:
    """Test custom host is used for API calls."""
    runtime = LMStudioRuntime(host="http://custom-host:9999")
    assert runtime._resolve_host() == "http://custom-host:9999"


def test_env_host_used_when_no_explicit_host() -> None:
    """Test environment variable host is used when no explicit host."""
    import os

    os.environ["LM_STUDIO_HOST"] = "http://envhost:8888"
    try:
        runtime = LMStudioRuntime()
        assert runtime._resolve_host() == "http://envhost:8888"
    finally:
        del os.environ["LM_STUDIO_HOST"]


def test_default_host_used_when_no_override() -> None:
    """Test default host is used when no override."""
    import os

    os.environ.pop("LM_STUDIO_HOST", None)
    runtime = LMStudioRuntime()
    assert runtime._resolve_host() == "http://localhost:1234"


# --- API key tests --------------------------------------------------------


def test_api_key_override_applied() -> None:
    """Test custom API key is used for authentication."""
    runtime = LMStudioRuntime(api_key="test-key-123")
    assert runtime._resolve_api_key() == "test-key-123"


def test_env_api_key_used_when_no_explicit_key() -> None:
    """Test environment variable API key is used when no explicit key."""
    import os

    os.environ["LM_API_TOKEN"] = "env-token-456"
    try:
        runtime = LMStudioRuntime()
        assert runtime._resolve_api_key() == "env-token-456"
    finally:
        del os.environ["LM_API_TOKEN"]


def test_default_api_key_used_when_no_override() -> None:
    """Test default API key is used when no override."""
    import os

    os.environ.pop("LM_API_TOKEN", None)
    runtime = LMStudioRuntime()
    assert runtime._resolve_api_key() is None


# --- default_tag_for tests ------------------------------------------------


def test_default_tag_for_returns_spec_default() -> None:
    """Test default_tag_for returns spec's default tag."""
    from modeldock.domain.model import Category, ModelSpec

    runtime = LMStudioRuntime()
    spec = ModelSpec(
        name="qwen",
        category=Category.CHAT,
        default_tag="qwen3.5-9b",
    )
    assert runtime.default_tag_for(spec) == "qwen3.5-9b"
