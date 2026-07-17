"""ModelDock domain layer — pure entities, no I/O."""

from modeldock.domain.backend import RuntimeBackend
from modeldock.domain.capability import Capability
from modeldock.domain.category import Category
from modeldock.domain.errors import AliasResolutionError, DomainError, ModelSpecError
from modeldock.domain.model import (
    ModelAlias,
    ModelRef,
    ModelSpec,
    ModelVariant,
)

__all__ = [
    "Capability",
    "Category",
    "RuntimeBackend",
    "ModelAlias",
    "ModelRef",
    "ModelSpec",
    "ModelVariant",
    "DomainError",
    "AliasResolutionError",
    "ModelSpecError",
]
