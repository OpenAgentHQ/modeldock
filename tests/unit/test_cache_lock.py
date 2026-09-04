"""Unit tests for the cross-process cache lock.

Two ``CacheLock`` instances behave like two processes: both `fcntl.flock` and
`msvcrt.locking` conflict between separate open file descriptions, even within
one interpreter, so exclusion is testable without spawning a subprocess.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from modeldock.adapters.cache.lock import LOCK_FILENAME, CacheLock


def _lock(tmp_path: Path, timeout: float = 30.0) -> CacheLock:
    return CacheLock(tmp_path / LOCK_FILENAME, timeout=timeout, poll=0.01)


def test_acquires_and_releases(tmp_path: Path) -> None:
    lock = _lock(tmp_path)
    assert not lock.held
    with lock:
        assert lock.held
        assert (tmp_path / LOCK_FILENAME).exists()
    assert not lock.held


def test_is_reentrant_within_a_thread(tmp_path: Path) -> None:
    """Locked methods call each other, so nesting must not deadlock."""
    lock = _lock(tmp_path)
    with lock:
        with lock:
            with lock:
                assert lock.held
            assert lock.held, "an inner exit must not release the lock"
        assert lock.held
    assert not lock.held


def test_releases_on_exception(tmp_path: Path) -> None:
    lock = _lock(tmp_path)
    # Nested rather than combined: __exit__ still receives the exception, but
    # the reachability of what follows stays obvious to readers and analyzers.
    # CodeQL reads the combined form as unreachable code, so ruff's preference
    # for merging these two context managers is suppressed here deliberately.
    with pytest.raises(RuntimeError):  # noqa: SIM117
        with lock:
            raise RuntimeError("boom")
    assert not lock.held
    # Still usable afterwards.
    with lock:
        assert lock.held


def test_excludes_a_second_holder(tmp_path: Path) -> None:
    """A second holder must not own the OS lock while the first holds it."""
    first = _lock(tmp_path)
    second = _lock(tmp_path, timeout=0.05)
    with first:
        with second:
            # Best effort: it proceeds after the timeout, but without the lock.
            assert not second.held
        assert first.held


def test_lock_is_reusable_after_the_holder_releases(tmp_path: Path) -> None:
    first = _lock(tmp_path)
    second = _lock(tmp_path, timeout=1.0)
    with first:
        pass
    with second:
        assert second.held


def test_serializes_threads(tmp_path: Path) -> None:
    """The in-process lock orders threads even where file locking is absent."""
    lock = _lock(tmp_path)
    order: list = []

    def worker(name: str) -> None:
        with lock:
            order.append(f"{name}:enter")
            order.append(f"{name}:exit")

    threads = [threading.Thread(target=worker, args=(str(i),)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(order) == 8
    # No thread's critical section is interleaved with another's.
    for index in range(0, len(order), 2):
        enter, exit_ = order[index], order[index + 1]
        assert enter.split(":")[0] == exit_.split(":")[0]
