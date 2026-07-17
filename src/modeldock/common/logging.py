"""Logging bootstrap for ModelDock.

Library-friendly: never calls ``logging.basicConfig()`` at import time. The
named logger ``modeldock`` is used everywhere; ``configure_logging`` is called
explicitly by CLI/entry points only. See Architecture.md §12.
"""

from __future__ import annotations

import logging
from typing import Optional

_LOGGER_NAME = "modeldock"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child of the ``modeldock`` named logger."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def configure_logging(
    level: str = "ERROR",
    fmt: Optional[str] = None,
    use_json: bool = False,
) -> logging.Logger:
    """Configure the ``modeldock`` root logger. Call only from entry points."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.ERROR))
    logger.handlers.clear()
    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(fmt or "%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class _JsonFormatter(logging.Formatter):
    """Minimal JSON line formatter for automation/CI."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


__all__ = ["get_logger", "configure_logging"]
