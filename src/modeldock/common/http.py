"""Shared httpx client factory.

Centralizes client construction (timeouts, retries, user-agent) so adapters
and the remote registry share one configuration. See Architecture.md §15.
"""

from __future__ import annotations

from typing import Dict, Optional

import httpx

from modeldock.common.logging import get_logger

_DEFAULT_TIMEOUT = 30.0
_USER_AGENT = "modeldock/0.1.0"


def create_client(
    timeout: float = _DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
    verify: bool = True,
) -> httpx.Client:
    """Create a configured synchronous httpx client."""
    merged = {"User-Agent": _USER_AGENT}
    if headers:
        merged.update(headers)
    logger = get_logger("http")
    logger.debug("Creating httpx client (timeout=%.1fs)", timeout)
    return httpx.Client(
        timeout=timeout,
        headers=merged,
        verify=verify,
        follow_redirects=True,
    )


def create_async_client(
    timeout: float = _DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
    verify: bool = True,
) -> httpx.AsyncClient:
    """Create a configured asynchronous httpx client."""
    merged = {"User-Agent": _USER_AGENT}
    if headers:
        merged.update(headers)
    return httpx.AsyncClient(
        timeout=timeout,
        headers=merged,
        verify=verify,
        follow_redirects=True,
    )


__all__ = ["create_client", "create_async_client"]
