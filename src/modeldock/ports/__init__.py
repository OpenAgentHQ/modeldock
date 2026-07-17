"""ModelDock port interfaces — typing.Protocol abstractions, no implementation."""

from modeldock.ports.cache import CachePort
from modeldock.ports.downloader import DownloaderPort
from modeldock.ports.events import EventPort
from modeldock.ports.progress import ProgressPort
from modeldock.ports.registry import RegistryPort
from modeldock.ports.runtime import PullResult, RuntimePort

__all__ = [
    "RuntimePort",
    "PullResult",
    "RegistryPort",
    "DownloaderPort",
    "CachePort",
    "ProgressPort",
    "EventPort",
]
