# Changelog

All notable changes to ModelDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project documentation set: `PROJECT.MD`, `Architecture.md`, `AGENT.md`, `QUICKSTART.md`, `Development.md`, `CONTEXT.md`, `INSTRUCTIONS.md`, `RELEASE.md`
- Package skeleton (`src/modeldock/`) following Clean Architecture: `domain`, `ports`, `core`, `adapters`, `cli`, `common`, `data`
- `pyproject.toml` with runtime/dev dependencies, `ollama`/`dev` extras, console script, and `modeldock.runtimes` entry point
- GitHub release workflow (`.github/workflows/release.yml`) using `uv`, with 3-way version consistency check and PyPI publish
- PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
- Contributor community files: `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, issue templates, `CODEOWNERS`

### Changed

- Renamed `PROBLEM.MD` to `PROJECT.MD` (product intent doc)

### Fixed

- None yet

## [0.1.0] - Unreleased

Initial pre-release. Documentation and package skeleton only; no implementation
code yet.

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible new functionality
- **PATCH**: Backward-compatible bug fixes

## Links

[Unreleased]: https://github.com/OpenAgentHQ/modeldock/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/OpenAgentHQ/modeldock/releases/tag/v0.1.0
