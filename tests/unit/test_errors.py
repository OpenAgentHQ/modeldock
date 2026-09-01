"""Unit tests for the ModelDock error hierarchy (coverage for error paths)."""

from __future__ import annotations

import pytest

from modeldock.common.errors import (
    AliasResolutionError,
    CacheError,
    ConfigError,
    DownloadError,
    ModelDockError,
    ModelNotFoundError,
    ModelNotInstalledError,
    RuntimeUnavailableError,
)


def test_modeldock_error_is_exception_subclass() -> None:
    assert issubclass(ModelDockError, Exception)


def test_modeldock_error_stores_and_stringifies_message() -> None:
    err = ModelDockError("something broke")
    assert err.message == "something broke"
    assert str(err) == "something broke"


def test_modeldock_error_raises_and_is_catchable() -> None:
    with pytest.raises(ModelDockError):
        raise ModelDockError("boom")


# --- RuntimeUnavailableError -------------------------------------------------


def test_runtime_unavailable_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise RuntimeUnavailableError("ollama")


def test_runtime_unavailable_error_message_without_hint() -> None:
    err = RuntimeUnavailableError("ollama")
    assert str(err) == "Runtime 'ollama' is not available or not running."


def test_runtime_unavailable_error_message_with_hint() -> None:
    err = RuntimeUnavailableError("ollama", hint="Start it with `ollama serve`.")
    assert str(err) == (
        "Runtime 'ollama' is not available or not running. Start it with `ollama serve`."
    )


# --- ModelNotFoundError -------------------------------------------------------


def test_model_not_found_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise ModelNotFoundError("mystery-model")


def test_model_not_found_error_message_includes_name() -> None:
    err = ModelNotFoundError("mystery-model")
    assert "mystery-model" in str(err)
    assert "modeldock search" in str(err)


# --- ModelNotInstalledError ---------------------------------------------------


def test_model_not_installed_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise ModelNotInstalledError("llama3")


def test_model_not_installed_error_message_without_auto_install() -> None:
    err = ModelNotInstalledError("llama3", auto_install=False)
    assert "not installed" in str(err)
    assert "modeldock install llama3" in str(err)
    assert "will be downloaded" not in str(err)


def test_model_not_installed_error_message_with_auto_install() -> None:
    err = ModelNotInstalledError("llama3", auto_install=True)
    assert "will be downloaded" in str(err)
    assert "auto_install is enabled" in str(err)


# --- DownloadError -------------------------------------------------------------


def test_download_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise DownloadError("llama3")


def test_download_error_message_without_reason() -> None:
    err = DownloadError("llama3")
    assert "Failed to download model 'llama3'." in str(err)
    assert "Reason:" not in str(err)
    assert "Check your network connection and retry." in str(err)


def test_download_error_message_with_reason() -> None:
    err = DownloadError("llama3", reason="checksum mismatch")
    assert "Reason: checksum mismatch" in str(err)


# --- CacheError ------------------------------------------------------------------


def test_cache_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise CacheError("manifest corrupt")


def test_cache_error_message_is_prefixed() -> None:
    err = CacheError("manifest corrupt")
    assert str(err) == "Cache error: manifest corrupt"


# --- ConfigError -----------------------------------------------------------------


def test_config_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise ConfigError("invalid log_level")


def test_config_error_message_is_prefixed() -> None:
    err = ConfigError("invalid log_level")
    assert str(err) == "Configuration error: invalid log_level"


# --- AliasResolutionError ---------------------------------------------------------


def test_alias_resolution_error_is_modeldock_error() -> None:
    with pytest.raises(ModelDockError):
        raise AliasResolutionError("ambiguous alias 'llama'")


def test_alias_resolution_error_message_is_prefixed() -> None:
    err = AliasResolutionError("ambiguous alias 'llama'")
    assert str(err) == "Alias resolution error: ambiguous alias 'llama'"


# --- __all__ / hierarchy sanity ----------------------------------------------------


@pytest.mark.parametrize(
    "error_cls",
    [
        RuntimeUnavailableError,
        ModelNotFoundError,
        ModelNotInstalledError,
        DownloadError,
        CacheError,
        ConfigError,
        AliasResolutionError,
    ],
)
def test_every_typed_error_subclasses_modeldock_error(error_cls: type) -> None:
    assert issubclass(error_cls, ModelDockError)
