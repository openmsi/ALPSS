# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-point PDV: `alpss_multipoint(config)` runs `alpss_main` once per probe,
  driven by a `multipoint` config section. New `alpss-multipoint` console
  script. Probes are not channels -- several probes may be wavelength
  multiplexed onto one oscilloscope channel, reading the same column but
  separated by frequency -- so the probe list comes from `multipoint.metadata`,
  never from the file. Probes sharing a channel read the trace once.
- `list_channels()` in `alpss.io.reading` enumerates the channels a file holds.
- `prescan_carrier()` in `alpss.carrier.frequency` locates the carrier in a raw
  trace before the domain of interest is known, so a wide search band can be
  narrowed onto the probe actually present. Reuses `carrier_frequency` rather
  than duplicating it.
- Per-probe outputs: figures are written per probe (`<stem>_probeN-plots.png`),
  while the data CSVs are written once, combined, with one column (or row) per
  probe on a shared time axis.

### Added
- `alpss_main(data, **inputs)` now takes an `(N, 2)` numpy array of
  `[time, voltage]`. Reading the file, flattening the config and validating it
  are the caller's job; `alpss_main_with_config` remains the file-based entry
  point and is unchanged. `run_velocity_phase(data, **inputs)` likewise takes
  the array.
- Multi-channel oscilloscope CSVs (e.g. Keysight exports with `Channel N`
  columns) are now readable. A new optional `channel` config key selects which
  channel to analyse; without it the first channel is read, so single-probe
  runs against a multi-channel file work unchanged.

### Changed
- The start of the numeric data is auto-detected instead of being taken from
  `header_lines`. The key is still accepted so existing configs keep loading,
  but its value is ignored and a warning is logged — it was wrong in most
  configs in use.
- **Repeatability baselines re-recorded.** Reading no longer lets pandas infer
  a header row after `skiprows`, which had been silently consuming the first
  data sample of every run. Results shift by one sample (e.g. time at max
  compression by 1.25e-11 s at 80 GHz); the new values are the correct ones.

### Fixed
- `plot_voltage` and `spall_doi_finder` no longer fail on a raw frame with more
  than two columns, so the error-path diagnostic plot works for multi-channel
  files.
- Otsu start detection no longer lands hundreds of ns late when the spectrogram
  has columns with no signal (e.g. a brief carrier dropout). Those columns are
  NaN in the top line, and `np.argmax` returned the first NaN instead of the
  highest point; it now uses `np.nanargmax` / `np.nanmean`.
- Otsu start detection raises a clear `ValueError` when no signal rises above
  the carrier band, instead of crashing with `UnboundLocalError: cidx`.

## [1.7.1] - 2026-06-09

### Changed
- Phase status display integrated into results table with color coding (velocity, spall & uncertainty, HEL)

## [1.7.0] - 2026-06-08

### Added
- Velocity phase now computes and tracks uncertainty (`velocity_ok` flag)
  - Velocity thresholds now required in config and properly enforced
- New shock analysis phase computing peak shock stress
- Enhanced config validation module with strict parameter checking and mode-based requirements
- New incompatibility check: HEL detection incompatible with gaussian_notch filter

### Changed
- **Major refactor**: Decoupled uncertainty analysis from spall phase; now runs independently
- Renamed config parameters: `spall_calculation` → `spall_enabled`, `hel_calculation` → `hel_enabled`
- Reorganized config structure for better clarity and validation
- Reorganized results output: velocity uncertainties moved to velocity phase, spall/shock/HEL results in their respective sections
- Improved error handling with per-phase error tracking and display on plots
- Pipeline phases now run independently with graceful degradation to NaN on failure
- Restructured internal phase orchestration in `utils/phases.py` for cleaner separation of concerns
- Reorganized modules structure for more readibility and practicality

## [1.6.0] - 2026-03-17

### Added
- `velocity_ok`, `spall_ok`, and `uncertainty_ok` flags in output, with per-category error messages

### Fixed
- Clamp `time_start_idx - pad` to valid range and use `np.pad(..., mode="edge")` to prevent empty arrays when signal starts near the beginning of data
- Removed internal try/except from `spall_analysis` so real exceptions surface to `alpss_main`
- Uncertainty analysis is now skipped when spall fails, preventing misleading `uncertainty_ok=True` with NaN values
- Hard HEL failures (insufficient data) raise; soft failures (no plateau) return `HELResult(ok=False, error_message=...)`
- HEL diagnostic figure is now saved via `save()` and returned in the assets dict

### Changed
- Reduced legend font size for "Voltage Data" and "Velocity with Uncertainty Bounds" plots
- Improved informational logging throughout the pipeline

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

[Unreleased]: https://github.com/openmsi/ALPSS/compare/v1.7.1...HEAD
[1.7.1]: https://github.com/openmsi/ALPSS/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/openmsi/ALPSS/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/openmsi/ALPSS/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/openmsi/ALPSS/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/openmsi/ALPSS/compare/v1.3.2...v1.4.0
[1.3.2]: https://github.com/openmsi/ALPSS/compare/v1.2.4...v1.3.2
[1.2.4]: https://github.com/openmsi/ALPSS/releases/tag/v1.2.4
