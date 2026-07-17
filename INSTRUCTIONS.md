# INSTRUCTIONS.md — How to Work in This Repo

Operational instructions for contributors and AI coding agents. Read
[`CONTEXT.md`](./CONTEXT.md) first for orientation, [`AGENT.md`](./AGENT.md)
for rules, [`Architecture.md`](./Architecture.md) for the design contract.

---

## 0. Before You Start

1. Read `CONTEXT.md`, `PROJECT.MD`, `Architecture.md`, `AGENT.md`.
2. Use ContextScout to discover any project-specific standards before coding.
 3. **No implementation without an approved plan.** When the user asks to
    implement any feature, bug fix, or refactor, you MUST: (a) read
    `QUICKSTART.md`, `AGENT.md`, and all files related to the task; (b) create
    a concrete execution plan; (c) request approval before writing any code
    (see §2).
4. **Create and activate a virtual environment** (`.venv`) and install all
   required libraries into it — never use global/system Python (see §1).
5. **ALWAYS work on a new branch** — never commit or push directly to `main`.
   Create a topic branch (see §2), push it, and open a PR for review. This
   applies to every change: docs, features, fixes, chores.

---

## 1. Environment (always use a virtual environment)

**ALWAYS work inside a virtual environment.** Never install packages into the
global/system Python. Create the venv, activate it, then install all required
libraries into that venv.

```bash
# Create and activate the virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install required libraries INTO the active venv
pip install -e ".[dev,ollama]"
pre-commit install
```

- Verify the venv is active before installing or running anything
  (`which python` / `where python` should point inside `.venv`).
- All dependencies (runtime + dev) live in the venv, not globally.
- If the shell is reset, re-activate `.venv` before any `pip`/`pytest`/`uv`
  command.

---

## 2. Workflow (mandatory)

```
branch → discover → propose → approve → init session → plan → execute → validate → PR
```

**Branch first (never work on `main`):**

```bash
git checkout main && git pull origin main
git checkout -b <type>/<desc>      # feature/, fix/, docs/, refactor/, test/, chore/
```

- **Branch:** create a topic branch from current `main` for every task.
- **Discover (mandatory before any plan):** When implementing a feature, bug
  fix, or refactor, you MUST first read the relevant files — at minimum
  `QUICKSTART.md` and `AGENT.md`, plus every file related to the task
  (e.g. the relevant `src/modeldock/` module, `Architecture.md` section,
  `pyproject.toml`, existing tests). Use ContextScout to surface related
  context. No files are written during discovery.
- **Plan (mandatory before any code):** Produce a concrete execution plan that
  lists the files to create/modify, the approach per file, the order of work,
  and how each step will be validated (type-check, lint, test). For multi-step
  work, break it into atomic subtasks and mark independent ones
  `parallel: true`.
- **Propose & approve:** Present the execution plan to the user and **request
  explicit approval**. Do NOT write or edit any implementation file until the
  user signs off.
- **Init session:** create `.tmp/sessions/<date>-<slug>/context.md`.
- **Execute:** one step at a time; validate (type-check, lint, test) after each.
- **Validate:** run full suite; suggest TestEngineer/CodeReviewer; summarize.
- **PR:** commit to the topic branch, push, and open a PR for review. Never
  self-merge; the user reviews and merges.

---

## 3. Where Code Lives

```
src/modeldock/
  domain/      pure entities, NO I/O, NO framework imports
  ports/       typing.Protocol interfaces, NO implementation
  core/        application services (depend on ports only)
  adapters/    runtimes, registry, downloaders, cache, progress
  cli/         Typer CLI, thin wrappers over core
  common/      config, logging, platform, http, errors
  data/        catalog.json (bundled registry)
```

**Dependency direction (never violate):**
`cli → core → ports ← adapters`; `domain`/`ports` import nothing from
`adapters`/`core`/`cli`.

---

## 4. Hard Rules (from AGENT.md)

- No code without an approved plan.
- **Before any feature/bugfix/refactor:** read `QUICKSTART.md`, `AGENT.md`, and
  all related files; create an execution plan; request approval before coding.
- **ALWAYS work on a new branch — never commit or push to `main`.**
- `domain/` and `ports/` stay pure (no I/O, no Ollama/HTTP/fs).
- Depend inward only.
- New runtimes = adapters + one entry-point line. **Never edit core/CLI/API.**
- No heavy ML deps (torch/transformers). Runtime SDKs are optional extras.
- Library-friendly logging: no `basicConfig()` at import.
- Typed errors (`ModelDockError` subclasses) with actionable context.
- Cross-platform: `platformdirs` for paths; no hardcoded `/` or `C:\`.

---

## 5. Quality Gates (run before committing)

```bash
ruff check src tests && ruff format src tests
mypy src
bandit -r src
pytest --cov=modeldock --cov-report=term-missing
pre-commit run --all-files
```

Targets: ruff clean, `mypy --strict` clean, bandit clean, ≥80% coverage.

---

## 6. Adding a Runtime (extension)

1. `src/modeldock/adapters/runtimes/<name>.py` implementing `RuntimePort`.
2. Subclass `BaseRuntime` for shared logic.
3. Add entry point in `pyproject.toml`:
   `[project.entry-points."modeldock.runtimes"] <name> = "..."`.
4. Add/extend port-contract tests; ensure they pass.
5. Do **not** touch `core/`, `cli/`, or `modeldock/__init__.py`.

---

## 7. Adding Models

Edit `src/modeldock/data/catalog.json`. No code change. See
[`Development.md`](./Development.md) §10 for the entry shape.

---

## 8. Testing Layers

| Layer | Needs | Run |
|---|---|---|
| Unit | nothing | `pytest tests/unit` |
| Port-contract | fake ports | `pytest -k contract` |
| Integration | Ollama | `pytest -m integration` (auto-skips if absent) |
| E2E | CLI | `pytest -m e2e` |

Use fake `RuntimePort`/`RegistryPort`/`CachePort` fixtures so core logic is
testable without a runtime.

---

## 9. Commit & PR

- **Always branch first** (see §0 step 5 and §2). Never commit or push to `main`.
- Commits: imperative, repo-style; never commit secrets or `.env`.
- PRs: reference the task; ensure CI green; update docs if behavior changed.
- Open the PR for the user to review — never self-merge.
- Only commit/push/PR when explicitly requested.

---

## 10. Doc Set (keep in sync)

`PROJECT.MD` (why) · `Architecture.md` (design) · `AGENT.md` (rules) ·
`QUICKSTART.md` (start) · `Development.md` (build) · `CONTEXT.md` (hub) ·
`INSTRUCTIONS.md` (this file) · `RELEASE.md` (release process).

When conflicts arise: `Architecture.md` > `AGENT.md` > others for design;
`PROJECT.MD` for product intent.

---

## 11. Writing Rules (GitHub content)

Rules for all generated GitHub content (issues, PRs, commits, docs).

### Markdown Rules

- Always use GitHub Flavored Markdown (GFM).
- Never generate malformed Markdown.
- Use proper `##` headings; never use bold text as headings.
- Wrap file paths in backticks: `src/modeldock/core/lifecycle.py`.
- Use forward slashes only (never `\`). **Never escape paths with backslashes**
  (no `\path\`); the backticks alone are sufficient.
- Never emit raw Unicode escapes like `\u00a7`; write the literal character
  (`§`) or use ASCII (`Section 2`).

### Code & Commands

- Fenced code blocks with language identifiers.
- Fenced `bash` blocks for commands.
- Never place multi-line code inline.

  ```python
  def hello() -> None:
      print("Hello")
  ```

### File Paths

- ✅ `src/modeldock/adapters/runtimes/ollama.py`
- ❌ `\src\modeldock\adapters\runtimes\ollama.py`

### Lists & Checklists

- Use proper Markdown lists.
- Use GitHub task lists: `- [ ] Tests added`.

### Templates

- **PR:** Summary · Changes · Testing · Checklist
- **Issue:** Description · Current Behavior · Expected Behavior · Files to Look
  At · Acceptance Criteria
- **Release Notes:** What's Changed · New Features · Bug Fixes · Documentation ·
  Tests · Contributors

### Tone

Professional maintainer. Clear, concise, technically accurate. At most one emoji
per section.

### Validation (before output)

Confirm: Markdown renders correctly · file paths use `/` · code blocks fenced ·
headings consistent · links formatted.
