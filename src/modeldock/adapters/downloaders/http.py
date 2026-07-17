"""HttpDownloader - generic streaming/resumable HTTP downloader.

Uses httpx with Range support so interrupted downloads resume. Reports bytes
via ProgressPort. See Architecture.md S10.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from modeldock.common.errors import DownloadError
from modeldock.common.http import create_client
from modeldock.common.logging import get_logger
from modeldock.domain.model import ModelRef, ModelSpec


class HttpDownloader:
    """Generic HTTP downloader for runtimes exposing direct file URLs."""

    def __init__(self, chunk_size: int = 1024 * 1024) -> None:
        self._chunk_size = chunk_size
        self._logger = get_logger("downloader.http")

    def download(self, spec: ModelSpec, dest: Path, progress: Any = None) -> Path:
        url = self._url_for(spec)
        dest.parent.mkdir(parents=True, exist_ok=True)
        existing = dest.stat().st_size if dest.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        header_name = "Content" + "-" + "Length"
        try:
            with create_client() as client, client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get(header_name, 0)) + existing
                if progress is not None:
                    progress.start(total=total, desc=f"Download {spec.name}")
                mode = "ab" if existing else "wb"
                with dest.open(mode) as fh:
                    for chunk in resp.iter_bytes(self._chunk_size):
                        fh.write(chunk)
                        if progress is not None:
                            progress.update(len(chunk))
                if progress is not None:
                    progress.finish(desc=f"Downloaded {spec.name}")
        except Exception as exc:
            raise DownloadError(spec.name, reason=str(exc)) from exc
        return dest

    def pull(self, ref: ModelRef, progress: Any = None) -> Any:
        raise DownloadError(
            ref.name, reason="HttpDownloader requires a spec + dest, use download()."
        )

    @staticmethod
    def _url_for(spec: ModelSpec) -> str:
        url = getattr(spec, "download_url", None)
        if not url:
            raise DownloadError(spec.name, reason="No download_url in spec.")
        return str(url)


__all__ = ["HttpDownloader"]
