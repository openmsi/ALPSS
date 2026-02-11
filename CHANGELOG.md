# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] - 2026-02-11

### Added
- Hugoniot Elastic Limit (HEL) detection module (`alpss.analysis.hel`)
  - `hel_detection()` — gradient-based plateau detection with configurable thresholds
  - `elastic_shock_strain_rate()` — elastic strain rate calculation
  - `HELResult` dataclass with typed fields for all detection outputs
- HEL diagnostic plotting (`alpss.plotting.hel.plot_hel_detection`)
  - 3-panel figure: full trace, zoomed plateau, gradient analysis
- HEL integrated into `alpss_main` pipeline as optional Phase 2b
  - Enabled via `hel_detection_enabled=True` in inputs
  - HEL results included in saved output CSV when detected
- Unit tests for HEL detection and strain rate calculation

## [1.4.0] - 2026-02-11

### Changed
- Reorganized codebase from flat layout to modular package structure under `src/alpss/`
- Moved carrier frequency and filter logic into `alpss.carrier` subpackage
- Moved spall and uncertainty analysis into `alpss.analysis` subpackage
- Moved velocity calculation into `alpss.velocity` subpackage
- Moved plotting into `alpss.plotting` subpackage
- Moved I/O and saving into `alpss.io` subpackage
- Moved detection logic into `alpss.detection` subpackage
- Moved shared utilities (`extract_data`, `stft`) into `alpss.utils`

### Added
- CLI entry points: `alpss` and `alpss-watch` commands
- Backward-compatible re-exports in `alpss.__init__` for existing user code
- Dynamic versioning via `poetry-dynamic-versioning` (git tag is single source of truth)
- `__version__` attribute exposed on the `alpss` package
- CI workflow for running tests on PRs and pushes to main
- Unified release workflow (test → PyPI → Docker → GitHub Release)
- `CHANGELOG.md` for tracking release history
- Changelog page in Jupyter Book documentation

### Fixed
- Dockerfile now pins the exact released version instead of using `--pre`

### Removed
- Old flat-layout module files (replaced by subpackage structure)

## [1.3.2] - 2024-12-01

### Changed
- Maintenance release with minor bug fixes and dependency updates

## [1.2.4] - 2024-05-01

### Added
- Time-resolved uncertainty estimates for velocity traces
- Automated spall signal analysis pipeline
- Initial PyPI and Docker publishing workflows

[Unreleased]: https://github.com/openmsi/ALPSS/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/openmsi/ALPSS/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/openmsi/ALPSS/compare/v1.3.2...v1.4.0
[1.3.2]: https://github.com/openmsi/ALPSS/compare/v1.2.4...v1.3.2
[1.2.4]: https://github.com/openmsi/ALPSS/releases/tag/v1.2.4
