"""ModelDock domain layer — pure business entities and value objects.

No I/O, no framework imports, no references to Ollama/HTTP/filesystem.
This module defines *what* a model is; adapters provide *how* it is obtained.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from modeldock.ports.registry import RegistryPort


class Capability(str, Enum):
    """Capabilities a model may expose."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBED = "embed"
    VISION = "vision"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"

    @classmethod
    def from_value(cls, value: str) -> Capability:
        """Resolve a capability from a string, case-insensitively."""
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown capability: {value!r}")


class Category(str, Enum):
    """High-level model categories used for discovery and bulk install."""

    CHAT = "chat"
    CODING = "coding"
    EMBEDDING = "embedding"
    VISION = "vision"
    REASONING = "reasoning"
    INSTRUCT = "instruct"

    @classmethod
    def from_value(cls, value: str) -> Category:
        """Resolve a category from a string, case-insensitively."""
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown category: {value!r}")


class RuntimeBackend(str, Enum):
    """Supported model runtimes. New runtimes register as adapters."""

    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"
    LLAMACPP = "llamacpp"
    JAN = "jan"
    GPT4ALL = "gpt4all"
    VLLM = "vllm"

    @classmethod
    def from_value(cls, value: str) -> RuntimeBackend:
        """Resolve a backend from a string, case-insensitively."""
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unknown runtime backend: {value!r}")


class ModelSize(BaseModel):
    """Value object representing a model's size: parameter count and disk footprint.

    Pure data — no I/O. Consolidates the loose ``params``/``size_bytes`` fields
    previously carried directly on ``ModelVariant``. See issue #98.
    """

    model_config = ConfigDict(frozen=True)

    params: int  # raw parameter count, e.g. 8_000_000_000
    size_bytes: int  # size on disk in bytes, e.g. 4_700_000_000

    def format_params(self) -> str:
        """Return a compact parameter count, e.g. '8B' or '1.5B'."""
        if self.params >= 1_000_000_000:
            value = self.params / 1_000_000_000
            suffix = "B"
        else:
            value = self.params / 1_000_000
            suffix = "M"
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"

    def format_size(self) -> str:
        """Return a human-readable disk size, e.g. '4.7GB'."""
        gb = self.size_bytes / (1000**3)
        text = f"{gb:.1f}".rstrip("0").rstrip(".")
        return f"{text}GB"

    def __str__(self) -> str:
        return f"{self.format_params()} ({self.format_size()})"


class ModelVariant(BaseModel):
    """A specific tag/variant of a model (e.g. llama3:8b)."""

    tag: str
    download_url: Optional[str] = None
    sha256: Optional[str] = None
    size: Optional[ModelSize] = None
    min_ram: Optional[str] = None


class ModelSpec(BaseModel):
    """Canonical, registry-described description of a model.

    Pure data — no I/O. Resolved from a friendly alias via ``ModelAlias``.
    """

    name: str
    aliases: List[str] = Field(default_factory=list)
    category: Category
    capabilities: List[Capability] = Field(default_factory=list)
    default_tag: str = "latest"
    variants: List[ModelVariant] = Field(default_factory=list)
    description: str = ""
    backend_hints: List[RuntimeBackend] = Field(default_factory=list)
    #: Human-facing provenance label of the source this spec came from
    #: (e.g. "Ollama Official", "Hugging Face"). ``None`` when unknown, so a
    #: spec built from a bare local ref carries no false provenance. Stamped by
    #: each registry adapter; see ``domain/source.py``.
    source: Optional[str] = None

    def default_variant(self) -> Optional[ModelVariant]:
        """Return the variant matching ``default_tag``, if present."""
        for variant in self.variants:
            if variant.tag == self.default_tag:
                return variant
        return None

    def version_tags(self) -> List[str]:
        """Return the known version tags for this model.

        The default tag leads, followed by every variant tag, deduplicated
        with order preserved. Used by ``RegistryPort.versions`` so callers can
        enumerate a model's variants without reaching into ``variants``.
        """
        tags: List[str] = []
        if self.default_tag:
            tags.append(self.default_tag)
        for variant in self.variants:
            if variant.tag not in tags:
                tags.append(variant.tag)
        return tags

    @classmethod
    def from_ref(cls, ref: ModelRef) -> ModelSpec:
        """Build a minimal spec for a model known only by a local ``ModelRef``.

        Used as a fallback when a model is installed locally but absent from the
        bundled catalog, so discovery/load still work. Carries no catalog
        metadata beyond the name and tag.
        """
        return cls(
            name=ref.name,
            default_tag=ref.tag,
            category=Category.CHAT,
            capabilities=[Capability.CHAT],
        )


class ModelInfo(BaseModel):
    """Catalog metadata enriched with the tags/versions installed locally.

    A superset of ``ModelSpec``: carries the same discovery metadata plus the
    concrete tags present in the active runtime (``installed_tags``) and a
    convenience ``installed`` flag. Pure data — no I/O. See issue #10.
    """

    name: str
    aliases: List[str] = Field(default_factory=list)
    category: Category
    capabilities: List[Capability] = Field(default_factory=list)
    default_tag: str = "latest"
    variants: List[ModelVariant] = Field(default_factory=list)
    description: str = ""
    backend_hints: List[RuntimeBackend] = Field(default_factory=list)
    source: Optional[str] = None
    installed_tags: List[str] = Field(default_factory=list)
    installed: bool = False

    @classmethod
    def from_spec(cls, spec: ModelSpec, installed_tags: List[str]) -> ModelInfo:
        """Build a ``ModelInfo`` from a catalog spec and locally installed tags."""
        tags = sorted(set(installed_tags))
        return cls(
            name=spec.name,
            aliases=list(spec.aliases),
            category=spec.category,
            capabilities=list(spec.capabilities),
            default_tag=spec.default_tag,
            variants=list(spec.variants),
            description=spec.description,
            backend_hints=list(spec.backend_hints),
            source=spec.source,
            installed_tags=tags,
            installed=bool(tags),
        )

    @classmethod
    def from_ref(cls, ref: ModelRef, installed_tags: List[str]) -> ModelInfo:
        """Build a minimal ``ModelInfo`` for a locally-installed, uncatalogued model.

        Fallback used when a model is installed but absent from the bundled
        catalog, so ``info()`` still returns useful data instead of raising.
        """
        tags = sorted(set(installed_tags))
        return cls(
            name=ref.name,
            default_tag=ref.tag,
            category=Category.CHAT,
            capabilities=[Capability.CHAT],
            installed_tags=tags,
            installed=bool(tags),
        )


class Device(str, Enum):
    """Execution device a runtime reports for a loaded model.

    ``UNKNOWN`` is used when the runtime cannot determine the device (e.g. the
    model is not loaded, or the runtime exposes no device metadata).
    """

    GPU = "gpu"
    CPU = "cpu"
    UNKNOWN = "unknown"


class RuntimeStatus(BaseModel):
    """Runtime execution status, including the device a model runs on.

    Pure data — no I/O. Adapters populate ``device`` from runtime metadata
    (e.g. Ollama ``ps`` VRAM usage). See issue #11.
    """

    backend: RuntimeBackend
    available: bool = False
    device: Device = Device.UNKNOWN
    loaded_models: List[str] = Field(default_factory=list)
    details: str = ""

    def __repr__(self) -> str:
        return f"RuntimeStatus({self.backend.value}, {self.device.value})"


class ModelRef(BaseModel):
    """A concrete reference to a model: name plus optional tag and backend."""

    name: str
    tag: str = "latest"
    backend: Optional[RuntimeBackend] = None

    @classmethod
    def parse(cls, value: str, backend: Optional[RuntimeBackend] = None) -> ModelRef:
        """Parse ``name`` or ``name:tag`` into a ``ModelRef``.

        Raises ``AliasResolutionError`` on empty input.
        """
        from modeldock.domain.errors import AliasResolutionError

        if not value or not value.strip():
            raise AliasResolutionError("Model reference cannot be empty")
        text = value.strip()
        if ":" in text:
            name, tag = text.split(":", 1)
            name, tag = name.strip(), tag.strip()
            if not name or not tag:
                raise AliasResolutionError(f"Invalid model reference: {value!r}")
        else:
            name, tag = text, "latest"
        return cls(name=name, tag=tag, backend=backend)

    def qualified_name(self) -> str:
        """Return ``name:tag`` form used by runtimes."""
        return f"{self.name}:{self.tag}"

    @property
    def is_cloud(self) -> bool:
        """True for cloud/subscription models (tag contains ``cloud``).

        These cannot be installed, run, or removed through a local runtime and
        must be short-circuited with a clear error instead of a daemon call.
        """
        return "cloud" in self.tag

    def __hash__(self) -> int:
        return hash((self.name, self.tag, self.backend))


class ModelAlias:
    """Pure alias-resolution rules mapping friendly names to canonical specs."""

    @staticmethod
    def resolve(value: str, registry: RegistryPort) -> ModelSpec:
        """Resolve a friendly name/tag to a ``ModelSpec`` via the registry.

        ``registry`` must expose ``get(ref: ModelRef) -> ModelSpec``.
        """
        from modeldock.domain.errors import AliasResolutionError

        if not value or not value.strip():
            raise AliasResolutionError("Cannot resolve empty model alias")
        ref = ModelRef.parse(value)
        try:
            return registry.get(ref)
        except Exception as exc:  # registry raises typed errors; re-wrap clearly
            raise AliasResolutionError(f"Could not resolve alias {value!r}: {exc}") from exc

    @staticmethod
    def matches_query(spec: ModelSpec, query: str) -> bool:
        """Return True if ``spec`` matches a free-text search ``query``."""
        q = query.strip().lower()
        if not q:
            return True
        haystack = [spec.name.lower(), spec.description.lower(), spec.category.value]
        haystack += [a.lower() for a in spec.aliases]
        haystack += [c.value for c in spec.capabilities]
        return any(q in field for field in haystack)
