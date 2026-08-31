"""Unit tests for common/platform.py, including Windows-specific path handling."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from modeldock.common import platform as md_platform


# ---------------------------------------------------------------------------
# Mocked tests — run on every OS, force Windows-style platformdirs output.
# ---------------------------------------------------------------------------

class TestWindowsPathsMocked:
    """Force platformdirs to return Windows-style paths and check our wrappers."""

    def test_user_config_dir_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            md_platform.platformdirs,
            "user_config_dir",
            lambda name, appauthor=False, roaming=True: r"C:\Users\test\AppData\Roaming\modeldock",
        )
        result = md_platform.user_config_dir()
        assert isinstance(result, Path)
        assert result == Path(r"C:\Users\test\AppData\Roaming\modeldock")

    def test_user_cache_dir_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            md_platform.platformdirs,
            "user_cache_dir",
            lambda name, appauthor=False: r"C:\Users\test\AppData\Local\modeldock\Cache",
        )
        result = md_platform.user_cache_dir()
        assert isinstance(result, Path)
        assert result == Path(r"C:\Users\test\AppData\Local\modeldock\Cache")

    def test_user_data_dir_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            md_platform.platformdirs,
            "user_data_dir",
            lambda name, appauthor=False: r"C:\Users\test\AppData\Local\modeldock",
        )
        result = md_platform.user_data_dir()
        assert isinstance(result, Path)
        assert result == Path(r"C:\Users\test\AppData\Local\modeldock")

    def test_system_config_dir_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            md_platform.platformdirs,
            "site_config_dir",
            lambda name: r"C:\ProgramData\modeldock",
        )
        result = md_platform.system_config_dir()
        assert isinstance(result, Path)
        assert result == Path(r"C:\ProgramData\modeldock")

    def test_default_cache_dir_windows_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MODELDOCK_CACHE_DIR", raising=False)
        monkeypatch.setattr(
            md_platform.platformdirs,
            "user_cache_dir",
            lambda name, appauthor=False: r"C:\Users\test\AppData\Local\modeldock",
        )
        result = md_platform.default_cache_dir()
        assert result == Path(r"C:\Users\test\AppData\Local\modeldock") / "models"

    def test_default_cache_dir_windows_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODELDOCK_CACHE_DIR", r"D:\ModelDockCache")
        result = md_platform.default_cache_dir()
        assert result == Path(r"D:\ModelDockCache")

    def test_is_windows_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(md_platform.os, "name", "nt")
        assert md_platform.is_windows() is True

    def test_is_windows_false_on_posix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(md_platform.os, "name", "posix")
        assert md_platform.is_windows() is False


# ---------------------------------------------------------------------------
# Real tests — only meaningful (and only run) on an actual Windows host,
# e.g. the Windows job in the CI matrix. Exercises real platformdirs
# behavior rather than mocks.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only path behavior")
class TestWindowsPathsReal:
    def test_is_windows_true_on_real_windows(self) -> None:
        assert md_platform.is_windows() is True

    def test_user_config_dir_under_real_appdata(self) -> None:
        result = md_platform.user_config_dir()
        appdata = os.environ["APPDATA"]
        assert str(result).lower().startswith(appdata.lower())

    def test_user_config_dir_not_doubled(self) -> None:
        """Regression test: appauthor must not default to appname
        (previously produced AppData\\Roaming\\modeldock\\modeldock)."""
        result = md_platform.user_config_dir()
        assert str(result).lower().count("modeldock") == 1

    def test_user_cache_dir_under_real_localappdata(self) -> None:
        result = md_platform.user_cache_dir()
        localappdata = os.environ["LOCALAPPDATA"]
        assert str(result).lower().startswith(localappdata.lower())

    def test_user_cache_dir_not_doubled(self) -> None:
        result = md_platform.user_cache_dir()
        assert str(result).lower().count("modeldock") == 1

    def test_paths_use_backslash_separators(self) -> None:
        result = md_platform.user_config_dir()
        # Real Windows paths render with backslashes via str(Path).
        assert "\\" in str(result)

    def test_default_cache_dir_env_override_with_windows_drive_letter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODELDOCK_CACHE_DIR", r"E:\Custom\Cache")
        result = md_platform.default_cache_dir()
        assert result == Path(r"E:\Custom\Cache")
        assert result.drive == "E:"