"""Cross-process advisory lock for the filesystem cache.

The cache directory is shared state: ``modeldock install`` in one terminal and
``modeldock cache clean`` in another touch the same ``manifest.json`` and the
same blob store. Every mutation is a read-modify-write, so a concurrent pair
can lose an entry or reclaim weights an in-flight install has not registered
yet. All mutating cache operations are serialized through one lock file.

Best effort by design. If the lock cannot be taken within ``timeout`` the
caller proceeds without it rather than failing a user's install — never worse
than the unsynchronized behaviour it replaces. The lock is advisory: it only
constrains processes that take it.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import time
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

from modeldock.common.logging import get_logger

# Platform-split so each side is only type-checked where it exists.
if sys.platform == "win32":
    try:
        import msvcrt

        _HAVE_LOCKING = True
    except ImportError:  # pragma: no cover - msvcrt ships with CPython on Windows
        _HAVE_LOCKING = False
else:
    try:
        import fcntl

        _HAVE_LOCKING = True
    except ImportError:  # pragma: no cover - exotic platform (wasm, some embeds)
        _HAVE_LOCKING = False

#: Filename of the lock, kept beside the manifest inside the cache dir.
LOCK_FILENAME = "cache.lock"


class CacheLock:
    """Re-entrant, cross-process advisory lock over a cache directory.

    Re-entrant per thread, so a locked public method may call another one
    without deadlocking. The OS-level lock is taken once, on the outermost
    entry, and released when the outermost block exits.
    """

    def __init__(self, path: Path, timeout: float = 30.0, poll: float = 0.05) -> None:
        self._path = Path(path)
        self._timeout = timeout
        self._poll = poll
        self._reentrant = threading.RLock()
        self._depth = 0
        self._fd: Optional[int] = None
        self._logger = get_logger("cache.lock")

    def __enter__(self) -> CacheLock:
        # The in-process lock is held for the whole critical section, so
        # threads serialize even where the platform offers no file locking.
        self._reentrant.acquire()
        self._depth += 1
        if self._depth == 1:
            self._acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self._depth -= 1
        if self._depth == 0:
            self._release()
        self._reentrant.release()

    @property
    def held(self) -> bool:
        """True when this instance currently owns the OS-level lock."""
        return self._fd is not None

    # --- internals --------------------------------------------------------

    def _acquire(self) -> None:
        if not _HAVE_LOCKING:  # pragma: no cover - exotic platform
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self._path), os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as exc:
            self._logger.debug("Could not open cache lock %s: %s", self._path, exc)
            return
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                _lock_fd(fd)
                self._fd = fd
                return
            except OSError:
                if time.monotonic() >= deadline:
                    self._logger.warning(
                        "Cache lock held by another process for %.0fs; proceeding without it",
                        self._timeout,
                    )
                    _close(fd)
                    return
                time.sleep(self._poll)

    def _release(self) -> None:
        fd = self._fd
        self._fd = None
        if fd is None:
            return
        try:
            _unlock_fd(fd)
        except OSError as exc:  # pragma: no cover - unlock rarely fails
            self._logger.debug("Could not release cache lock: %s", exc)
        _close(fd)


def _lock_fd(fd: int) -> None:
    """Take an exclusive lock on ``fd``, raising OSError if already held."""
    if sys.platform == "win32":
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_fd(fd: int) -> None:
    if sys.platform == "win32":
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _close(fd: int) -> None:
    with contextlib.suppress(OSError):
        os.close(fd)


__all__ = ["CacheLock", "LOCK_FILENAME"]
