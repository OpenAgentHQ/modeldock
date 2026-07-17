# RELEASE.md — ModelDock Release Checklist

Quick reference for releasing new versions of ModelDock.

Repo: https://github.com/OpenAgentHQ/modeldock.git
Package: `modeldock` · Console script: `modeldock` · Module: `python -m modeldock`
Build/Release tooling: **uv** + `.github/workflows/release.yml`

---

## Pre-Release

- [ ] All tests pass (`pytest`)
- [ ] Linting passes (`ruff check src tests`)
- [ ] Formatting passes (`ruff format src tests`)
- [ ] Type checking passes (`mypy src`)
- [ ] Security scan clean (`bandit -r src`)
- [ ] CI is green (Windows/macOS/Linux × Python 3.9–3.12)
- [ ] Package builds successfully (`uv build`)
- [ ] Documentation is up to date (`PROJECT.MD`, `Architecture.md`, `AGENT.md`,
      `QUICKSTART.md`, `Development.md`, `CONTEXT.md`, `INSTRUCTIONS.md`)

---

## Update Version

- [ ] Update `pyproject.toml` version
- [ ] Update `src/modeldock/__init__.py` `__version__` (must match)
- [ ] Update `CHANGELOG.md` with all changes since last release
- [ ] Update comparison links in `CHANGELOG.md`

```python
# src/modeldock/__init__.py
__version__ = "0.1.0"
```

---

## Create Release Branch & PR

```bash
git checkout main
git pull origin main
git checkout -b release/vX.Y.Z
git add pyproject.toml src/modeldock/__init__.py CHANGELOG.md uv.lock
git commit -m "chore: release vX.Y.Z"
git push -u origin release/vX.Y.Z
gh pr create --title "chore: release vX.Y.Z" --base main
```

- [ ] PR created and reviewed
- [ ] PR merged

---

## Tag Release

Pushing the tag is the **only manual action** required to ship. The
`.github/workflows/release.yml` workflow is triggered automatically by the tag
push (`on: push: tags: ["v*.*.*"]`) and runs the entire release pipeline with
no further human intervention:

1. **Verify version consistency** — asserts `pyproject.toml` version ==
   `src/modeldock/__init__.py` `__version__` == tag (fails the build on mismatch).
2. **Run quality gates** — `ruff check`, `ruff format --check`, `mypy src`,
   `bandit -r src`, `pytest`.
3. **Build distributions** — `uv build` (sdist + wheel).
4. **Publish to PyPI** — `pypa/gh-action-pypi-publish` via trusted publishing (OIDC).
5. **Create GitHub Release** — `gh release create` with auto-generated notes.

Do **not** run these steps manually at release time; the workflow handles them.
Just create and push the tag:

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

- [ ] Tag created and pushed (this auto-triggers the release workflow)
- [ ] Release workflow completed: quality gates passed, built, published to PyPI, GitHub Release created

> **Prerequisites (repo settings, one-time):** the `pypi` environment must be
> configured with PyPI trusted publishing for `modeldock`, and the workflow's
> `contents: write` permission must allow `gh release create`. If either is
> missing, the publish or release step fails even though earlier steps pass.

---

## GitHub Release

> **Automatic.** The release workflow creates the GitHub Release on tag push
> (step 5 above) using `gh release create --generate-notes`. No manual creation
> is needed. If you prefer a hand-written title/notes, you may delete the
> auto-created release and recreate it manually after the workflow finishes.

- [ ] GitHub Release created automatically by the workflow (title `vX.Y.Z`, auto-generated notes)
- [ ] Release notes include PR links: `- **Name** — description (#PR_NUMBER)`
- [ ] Release notes include Contributors section

---

## Post-Release Verification

- [ ] Git tag exists (`git tag -l "vX.Y.Z"`)
- [ ] GitHub Release exists (`gh release view vX.Y.Z`)
- [ ] Package available on PyPI (`pip install modeldock==X.Y.Z`)
- [ ] `uv build` artifacts published (sdist + wheel)
- [ ] CLI reports correct version (`modeldock --version`)
- [ ] CI workflow completed successfully

---

## Semantic Versioning

| Change | Example |
|---|---|
| PATCH (bug fixes, docs, internal) | 0.1.0 → 0.1.1 |
| MINOR (backward-compatible features) | 0.1.0 → 0.2.0 |
| MAJOR (breaking changes) | 1.x.x → 2.0.0 |

---

## Release Notes Format

```markdown
## What's Changed

### ✨ Features
- **Feature Name** — description (#PR_NUMBER)

### 🐛 Bug Fixes
- **Fix Name** — description (#PR_NUMBER)

### 📚 Documentation
- **Doc Change** — description (#PR_NUMBER)

### ⚙️ Testing
- **Test Change** — description (#PR_NUMBER)

### ⚙️ Internal
- **Internal Change** — description (#PR_NUMBER)

### ❤️ Contributors
- @contributor1

**Full Changelog**: https://github.com/OpenAgentHQ/modeldock/compare/vPREV...vX.Y.Z
```

---

## Files Involved

| File | Purpose |
|---|---|
| `pyproject.toml` | Canonical version |
| `src/modeldock/__init__.py` | Runtime version (`__version__`) |
| `CHANGELOG.md` | Release history |
| `uv.lock` | Lock file (committed) |
| `.github/workflows/release.yml` | PyPI publish via `uv` |

---

## Troubleshooting

**Version mismatch**
Always update both `pyproject.toml` and `src/modeldock/__init__.py` — they must
match, and both must equal the git tag (without the `v` prefix). The
`release.yml` workflow asserts all three are equal and fails the build
otherwise.

**Push rejected**
Use the PR workflow — direct push to `main` is blocked by branch protection.

**Tag exists by mistake**
```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```
