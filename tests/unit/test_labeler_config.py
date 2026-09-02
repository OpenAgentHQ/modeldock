"""Tests for the path-based PR labeler configuration.

Validates ``.github/labeler.yml`` against the real repository tree so a stale
glob (a directory that was renamed or removed) fails CI instead of silently
labeling nothing:
  - the areas named in the acceptance criteria all exist
  - every glob still matches at least one tracked path
  - the globs actually route the areas they claim to route
  - every configured label is created by the workflow's bootstrap step
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LABELER_CONFIG = REPO_ROOT / ".github" / "labeler.yml"
LABELER_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "labeler.yml"

# Areas the issue requires; extras (tests, ci) are allowed but not mandated.
REQUIRED_AREAS = ("cli", "core", "adapters", "docs")

# Directories that are never part of a pull request diff.
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "site",
        ".idea",
        ".vscode",
    }
)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate the minimatch subset used by actions/labeler to a regex.

    ``**/`` spans any number of directories, ``**`` spans the rest of the path,
    and ``*``/``?`` stay within a single path segment.
    """
    out: List[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _repo_files() -> List[str]:
    """POSIX-style repo-relative paths of every file a PR could touch."""
    paths: List[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        if _SKIP_DIRS.intersection(relative.parts):
            continue
        paths.append(relative.as_posix())
    return paths


def _config() -> Dict[str, Any]:
    return yaml.safe_load(LABELER_CONFIG.read_text(encoding="utf-8"))


def _globs_for(label: str) -> List[str]:
    """Flatten the ``changed-files``/``any-glob-to-any-file`` nesting."""
    globs: List[str] = []
    for rule in _config()[label]:
        for matcher in rule.get("changed-files", []):
            globs.extend(matcher.get("any-glob-to-any-file", []))
    return globs


def _all_globs() -> Iterator[tuple]:
    for label in _config():
        for glob in _globs_for(label):
            yield label, glob


def _labels_for(path: str) -> List[str]:
    """The labels the config would apply to a PR touching ``path``."""
    return [
        label
        for label in _config()
        if any(_glob_to_regex(glob).match(path) for glob in _globs_for(label))
    ]


@pytest.fixture(scope="module")
def repo_files() -> List[str]:
    return _repo_files()


# ─── Structure ──────────────────────────────────────────────────────────────


def test_labeler_config_exists_and_parses() -> None:
    assert LABELER_CONFIG.is_file(), "missing .github/labeler.yml"
    assert isinstance(_config(), dict)


@pytest.mark.parametrize("area", REQUIRED_AREAS)
def test_required_area_is_configured(area: str) -> None:
    assert f"area: {area}" in _config(), f"no rule for 'area: {area}'"


def test_every_label_has_at_least_one_glob() -> None:
    for label in _config():
        assert _globs_for(label), f"{label}: no any-glob-to-any-file patterns"


# ─── Globs match the real tree ──────────────────────────────────────────────


@pytest.mark.parametrize("label,glob", list(_all_globs()), ids=lambda v: str(v))
def test_glob_matches_a_real_path(label: str, glob: str, repo_files: List[str]) -> None:
    """A glob matching nothing means the mapping went stale."""
    matcher = _glob_to_regex(glob)
    assert any(matcher.match(path) for path in repo_files), (
        f"{label}: glob '{glob}' matches no file in the repository"
    )


# ─── Routing ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path,expected",
    [
        ("src/modeldock/cli/app.py", "area: cli"),
        ("src/modeldock/cli/commands/install.py", "area: cli"),
        ("src/modeldock/core/manager.py", "area: core"),
        ("src/modeldock/domain/model.py", "area: core"),
        ("src/modeldock/ports/cache.py", "area: core"),
        ("src/modeldock/common/config.py", "area: core"),
        ("src/modeldock/adapters/cache/filesystem.py", "area: adapters"),
        ("src/modeldock/adapters/runtimes/ollama.py", "area: adapters"),
        ("docs/index.md", "area: docs"),
        ("README.md", "area: docs"),
        ("mkdocs.yml", "area: docs"),
        ("tests/unit/test_cache.py", "area: tests"),
        (".github/workflows/labeler.yml", "area: ci"),
        ("pyproject.toml", "area: ci"),
    ],
)
def test_path_routes_to_expected_area(path: str, expected: str) -> None:
    assert expected in _labels_for(path), f"{path} should be labeled '{expected}'"


def test_cli_change_does_not_label_adapters() -> None:
    """Areas must not overlap, or every PR ends up wearing every label."""
    assert _labels_for("src/modeldock/cli/app.py") == ["area: cli"]


def test_multi_area_pr_gets_every_touched_label() -> None:
    touched = ["src/modeldock/cli/app.py", "docs/index.md"]
    labels = {label for path in touched for label in _labels_for(path)}
    assert labels == {"area: cli", "area: docs"}


# ─── Workflow wiring ────────────────────────────────────────────────────────


def test_workflow_points_at_this_config() -> None:
    workflow = LABELER_WORKFLOW.read_text(encoding="utf-8")
    assert "actions/labeler@v5" in workflow
    assert "configuration-path: .github/labeler.yml" in workflow


def test_workflow_does_not_strip_manual_labels() -> None:
    workflow = LABELER_WORKFLOW.read_text(encoding="utf-8")
    assert "sync-labels: false" in workflow


def test_workflow_bootstraps_every_configured_label() -> None:
    """Each label in the config is created by the ensure-labels step."""
    workflow = LABELER_WORKFLOW.read_text(encoding="utf-8")
    for label in _config():
        assert f"'{label}'" in workflow, f"{label} is never created by labeler.yml"
