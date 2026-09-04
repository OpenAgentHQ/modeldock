"""Tests for GitHub Actions workflow permission least-privilege compliance.

Validates that every workflow under .github/workflows/ follows the
least-privilege principle required by AGENT.md:
  - No top-level write-all / admin permissions
  - Sensitive scopes (id-token, pages, contents:write) are scoped to the
    jobs that actually need them
  - Every workflow has an explicit top-level permissions block
  - YAML structure is well-formed
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

# ─── Helpers ────────────────────────────────────────────────────────────────

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# GitHub-recognized permission scopes
KNOWN_SCOPES = frozenset(
    {
        "actions",
        "attestations",
        "checks",
        "contents",
        "deployments",
        "discussions",
        "id-token",
        "issues",
        "packages",
        "pages",
        "pull-requests",
        "repository-projects",
        "security-events",
        "statuses",
    }
)

# Maximum allowed permission level for top-level blocks
# write-all or admin at top level is always over-broad
FORBIDDEN_TOP_LEVEL_VALUES = {"write-all", "admin"}


def _load_workflow(name: str) -> Dict[str, Any]:
    """Load and parse a workflow YAML file."""
    path = WORKFLOWS_DIR / name
    assert path.exists(), f"Workflow file not found: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _all_workflow_files() -> List[str]:
    """Return basenames of all .yml workflow files."""
    return sorted(f.name for f in WORKFLOWS_DIR.glob("*.yml"))


def _get_top_permissions(data: Dict[str, Any]) -> Dict[str, str] | None:
    """Extract the top-level permissions block (may be None)."""
    return data.get("permissions")


def _get_job_permissions(data: Dict[str, Any], job_name: str) -> Dict[str, str] | None:
    """Extract the permissions block for a specific job."""
    jobs = data.get("jobs", {})
    job = jobs.get(job_name, {})
    return job.get("permissions")


def _effective_permissions(
    top: Dict[str, str] | None,
    job: Dict[str, str] | None,
) -> Dict[str, str]:
    """Compute the effective permissions for a job.

    GitHub rules: if a job defines its own permissions block, it completely
    overrides the top-level block (no merging).
    """
    if job is not None:
        return dict(job)
    if top is not None:
        return dict(top)
    # No permissions block at all → GitHub default (liberal)
    return {}


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(params=_all_workflow_files(), ids=_all_workflow_files())
def workflow_file(request: pytest.FixtureRequest) -> str:
    """Parametrised fixture yielding each workflow filename."""
    return request.param


@pytest.fixture
def workflow_data(workflow_file: str) -> Dict[str, Any]:
    """Parsed YAML data for a workflow file."""
    return _load_workflow(workflow_file)


# ═══════════════════════════════════════════════════════════════════════════
# 1. STRUCTURAL TESTS — Every workflow is well-formed
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowStructure:
    """Basic YAML structure and required keys."""

    def test_yaml_parses_successfully(self, workflow_file: str) -> None:
        """Each workflow file must be valid YAML."""
        path = WORKFLOWS_DIR / workflow_file
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{workflow_file} did not parse to a dict"

    def test_has_name(self, workflow_data: Dict[str, Any], workflow_file: str) -> None:
        assert "name" in workflow_data, f"{workflow_file}: missing 'name'"

    def test_has_trigger(self, workflow_data: Dict[str, Any], workflow_file: str) -> None:
        # PyYAML parses 'on' as boolean True
        has_on = "on" in workflow_data or True in workflow_data
        assert has_on, f"{workflow_file}: missing 'on' trigger"

    def test_has_jobs(self, workflow_data: Dict[str, Any], workflow_file: str) -> None:
        assert "jobs" in workflow_data, f"{workflow_file}: missing 'jobs'"

    def test_has_explicit_permissions_block(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """Every workflow MUST declare a top-level permissions block."""
        perms = _get_top_permissions(workflow_data)
        assert perms is not None, (
            f"{workflow_file}: missing top-level 'permissions' block. "
            "All workflows must explicitly restrict permissions."
        )

    def test_permissions_use_known_scopes(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """All declared scopes must be valid GitHub permission scopes."""
        top_perms = _get_top_permissions(workflow_data) or {}
        for scope in top_perms:
            assert scope in KNOWN_SCOPES, f"{workflow_file}: unknown top-level scope '{scope}'"

        for job_name, job_def in workflow_data.get("jobs", {}).items():
            job_perms = job_def.get("permissions") or {}
            for scope in job_perms:
                assert scope in KNOWN_SCOPES, (
                    f"{workflow_file} job '{job_name}': unknown scope '{scope}'"
                )


# ═══════════════════════════════════════════════════════════════════════════
# 2. GLOBAL LEAST-PRIVILEGE TESTS — Apply to every workflow
# ═══════════════════════════════════════════════════════════════════════════


class TestGlobalLeastPrivilege:
    """Rules that must hold for ALL workflows."""

    def test_no_top_level_write_all(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """Top-level permissions must not be 'write-all' or 'admin'."""
        perms = _get_top_permissions(workflow_data)
        if isinstance(perms, str):
            assert perms not in FORBIDDEN_TOP_LEVEL_VALUES, (
                f"{workflow_file}: top-level permissions '{perms}' is too broad"
            )

    def test_top_level_has_no_id_token_write(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """id-token: write should never appear at top level.

        OIDC tokens are sensitive and must be scoped to the specific job
        that actually performs Trusted Publishing or Pages deployment.
        """
        perms = _get_top_permissions(workflow_data) or {}
        assert perms.get("id-token") != "write", (
            f"{workflow_file}: 'id-token: write' at top level is over-broad. "
            "Move it to the specific job that needs OIDC."
        )

    def test_top_level_has_no_pages_write(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """pages: write should never appear at top level.

        Only the actual deploy job needs this scope.
        """
        perms = _get_top_permissions(workflow_data) or {}
        assert perms.get("pages") != "write", (
            f"{workflow_file}: 'pages: write' at top level is over-broad. "
            "Move it to the deploy job."
        )

    def test_top_level_has_no_contents_write(
        self, workflow_data: Dict[str, Any], workflow_file: str
    ) -> None:
        """contents: write should never appear at top level.

        If a specific job needs write access to contents, scope it there.
        """
        perms = _get_top_permissions(workflow_data) or {}
        assert perms.get("contents") != "write", (
            f"{workflow_file}: 'contents: write' at top level is over-broad. "
            "Scope it to the job that needs it."
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. PER-WORKFLOW PERMISSION TESTS — File-specific assertions
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckWorkflow:
    """Permissions for check.yml (CI: lint, test, CodeQL)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("check.yml")

    def test_top_level_is_contents_read_only(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {"contents": "read"}

    def test_quality_and_test_inherits_read_only(self) -> None:
        """The quality-and-test job only checks out code and runs linters."""
        job_perms = _get_job_permissions(self.data, "quality-and-test")
        assert job_perms is None, "quality-and-test should inherit top-level"

    def test_coverage_inherits_read_only(self) -> None:
        job_perms = _get_job_permissions(self.data, "coverage")
        assert job_perms is None, "coverage should inherit top-level"

    def test_codeql_has_scoped_permissions(self) -> None:
        job_perms = _get_job_permissions(self.data, "codeql")
        assert job_perms is not None
        assert job_perms.get("security-events") == "write"
        assert job_perms.get("packages") == "read"
        # Must NOT have contents: write or id-token: write
        assert "id-token" not in job_perms
        assert job_perms.get("contents") != "write"


class TestCongratsWorkflow:
    """Permissions for congrats.yml (PR congratulations comment)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("congrats.yml")

    def test_top_level_permissions(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {"pull-requests": "write", "contents": "read"}

    def test_congratulate_inherits_top_level(self) -> None:
        job_perms = _get_job_permissions(self.data, "congratulate")
        assert job_perms is None


class TestDeployWorkflow:
    """Permissions for deploy.yml (MkDocs -> GitHub Pages)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("deploy.yml")

    def test_top_level_is_contents_read_only(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {"contents": "read"}

    def test_build_job_has_no_extra_permissions(self) -> None:
        """Build job only checks out code and runs mkdocs -- needs nothing else."""
        job_perms = _get_job_permissions(self.data, "build")
        assert job_perms is None, "build job should inherit top-level (contents: read) only"
        # Verify effective permissions
        top = _get_top_permissions(self.data)
        effective = _effective_permissions(top, job_perms)
        assert effective == {"contents": "read"}

    def test_deploy_job_has_pages_and_id_token(self) -> None:
        """Deploy job needs pages: write and id-token: write."""
        job_perms = _get_job_permissions(self.data, "deploy")
        assert job_perms is not None, "deploy job must have its own permissions block"
        assert job_perms.get("pages") == "write"
        assert job_perms.get("id-token") == "write"

    def test_deploy_job_does_not_have_contents_write(self) -> None:
        job_perms = _get_job_permissions(self.data, "deploy") or {}
        assert job_perms.get("contents") != "write"


class TestIssueClaimWorkflow:
    """Permissions for issue-claim.yml (slash-command issue assignment)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("issue-claim.yml")

    def test_top_level_permissions(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {
            "issues": "write",
            "contents": "read",
            "pull-requests": "read",
        }

    def test_issue_claim_inherits_top_level(self) -> None:
        job_perms = _get_job_permissions(self.data, "issue-claim")
        assert job_perms is None


class TestReleaseWorkflow:
    """Permissions for release.yml (PyPI publish + GitHub Release)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("release.yml")

    def test_top_level_is_contents_read_only(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {"contents": "read"}

    def test_publish_job_has_id_token_write(self) -> None:
        """Publish job needs OIDC for Trusted Publishing."""
        job_perms = _get_job_permissions(self.data, "publish")
        assert job_perms is not None, "publish job must have its own permissions block"
        assert job_perms.get("id-token") == "write"
        assert job_perms.get("contents") == "read"

    def test_release_artifacts_has_contents_write_only(self) -> None:
        """release-artifacts uploads to GitHub Release -- needs contents: write."""
        job_perms = _get_job_permissions(self.data, "release-artifacts")
        assert job_perms is not None
        assert job_perms.get("contents") == "write"
        # Must NOT have id-token: write
        assert "id-token" not in job_perms, "release-artifacts must not have id-token: write"

    def test_release_artifacts_does_not_inherit_id_token(self) -> None:
        """Verify id-token: write does NOT leak to release-artifacts."""
        top = _get_top_permissions(self.data)
        job_perms = _get_job_permissions(self.data, "release-artifacts")
        effective = _effective_permissions(top, job_perms)
        assert effective.get("id-token") != "write", (
            "id-token: write leaked to release-artifacts via top-level permissions"
        )


class TestLabelerWorkflow:
    """Permissions for labeler.yml (path-based PR area labels)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.data = _load_workflow("labeler.yml")

    def test_top_level_permissions(self) -> None:
        perms = _get_top_permissions(self.data)
        assert perms == {
            "contents": "read",
            "pull-requests": "write",
            "issues": "write",
        }

    def test_label_job_inherits_top_level(self) -> None:
        job_perms = _get_job_permissions(self.data, "label")
        assert job_perms is None

    def test_runs_on_pull_request_target(self) -> None:
        """Fork PRs only get a writable token via pull_request_target."""
        # PyYAML parses the 'on' key as boolean True.
        triggers = self.data.get("on", self.data.get(True, {}))
        assert "pull_request_target" in triggers, (
            "labeler.yml must use pull_request_target so PRs from forks get labeled"
        )

    def test_does_not_check_out_pull_request_code(self) -> None:
        """pull_request_target is only safe while no PR code is checked out."""
        steps = self.data["jobs"]["label"]["steps"]
        assert not any("actions/checkout" in str(step.get("uses", "")) for step in steps), (
            "labeler.yml must not check out untrusted PR code under pull_request_target"
        )
