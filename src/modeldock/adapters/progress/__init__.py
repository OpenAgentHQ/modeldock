"""ModelDock progress reporters implementing ProgressPort."""

from modeldock.adapters.progress.rich_progress import RichProgress
from modeldock.adapters.progress.silent import SilentProgress
from modeldock.adapters.progress.tqdm_progress import TqdmProgress
from modeldock.ports.progress import ProgressPort


def make_progress(style: str) -> ProgressPort:
    """Factory: build a ProgressPort by style name (rich/tqdm/silent)."""
    style = (style or "rich").lower()
    if style == "silent":
        return SilentProgress()
    if style == "tqdm":
        return TqdmProgress()
    return RichProgress()


__all__ = ["RichProgress", "TqdmProgress", "SilentProgress", "make_progress"]
