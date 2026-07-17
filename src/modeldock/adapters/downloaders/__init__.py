"""ModelDock downloader adapters."""

from modeldock.adapters.downloaders.http import HttpDownloader
from modeldock.adapters.downloaders.ollama_pull import OllamaPullDownloader

__all__ = ["HttpDownloader", "OllamaPullDownloader"]
