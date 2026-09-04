"""ModelDock port interfaces — typing.Protocol abstractions, no implementation."""

from modeldock.ports.cache import CachePort, ContentStorePort
from modeldock.ports.catalog_provider import CatalogProvider
from modeldock.ports.downloader import DownloaderPort
from modeldock.ports.events import EventPort
from modeldock.ports.progress import ProgressPort
from modeldock.ports.registry import RegistryPort
from modeldock.ports.runtime import PullResult, RuntimePort

__all__ = [
    "RuntimePort",
    "PullResult",
    "RegistryPort",
    "CatalogProvider",
    "DownloaderPort",
    "CachePort",
    "ContentStorePort",
    "ProgressPort",
    "EventPort",
]
