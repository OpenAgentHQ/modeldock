"""ModelDock adapter/infrastructure layer."""

from modeldock.adapters.cache import FilesystemCache
from modeldock.adapters.downloaders import HttpDownloader, OllamaPullDownloader
from modeldock.adapters.progress import (
    RichProgress,
    SilentProgress,
    TqdmProgress,
    make_progress,
)
from modeldock.adapters.registry import BundledRegistry, RemoteRegistry
from modeldock.adapters.runtimes import (
    BaseRuntime,
    Gpt4AllRuntime,
    JanRuntime,
    LlamaCppRuntime,
    LMStudioRuntime,
    OllamaRuntime,
    RuntimeRegistry,
    VllmRuntime,
)

__all__ = [
    "BaseRuntime",
    "OllamaRuntime",
    "LMStudioRuntime",
    "LlamaCppRuntime",
    "JanRuntime",
    "Gpt4AllRuntime",
    "VllmRuntime",
    "RuntimeRegistry",
    "BundledRegistry",
    "RemoteRegistry",
    "HttpDownloader",
    "OllamaPullDownloader",
    "FilesystemCache",
    "RichProgress",
    "TqdmProgress",
    "SilentProgress",
    "make_progress",
]
