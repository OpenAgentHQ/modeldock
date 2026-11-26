"""Domain alias-resolution helpers — re-exported for convenience."""

import re

from modeldock.domain.model import ModelAlias

__all__ = ["ModelAlias", "normalize_alias"]


def normalize_alias(value: str) -> str:
    """Normalize a model alias for deterministic matching."""
    return re.sub(r"[-_\s]+", "", value.strip().lower())
