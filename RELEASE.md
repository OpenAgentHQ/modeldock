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

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

- [ ] Tag created and pushed

---

## GitHub Release

- [ ] GitHub Release created with descriptive title: `vX.Y.Z – [Title]`
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
