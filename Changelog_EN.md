# Changelog

Record of all notable changes in the NTS Automation System project.

## [2.9.0] - 2026-11-03 - DD / STEP / SC spatial schemes

### Added
- `SPATIAL_SCHEME` in the 1D configuration (`"DD"`, `"STEP"`, `"SC"`;
  default `"DD"`).
- Cell kernels `_cell_out_dd`, `_cell_out_step`, `_cell_out_sc`,
  `cell_out()` and `cell_average()` in `NTS_DD_1D.py`.
- `theta_step_characteristic()` with a series for `α < 1e-3` and rejection
  of negative optical thickness.
- `Config.theta_sc` precomputed once per run, shape `(NTC, N_HALF)`.
- Scheme prompt in the manual wizard and in `nts-1d-config`.
- `tests/test_spatial_schemes.py` (29 tests).
- `doc/SPATIAL_SCHEMES_EN.md` and `doc/SPATIAL_SCHEMES.md`.

### Changed
- `Method` uses string values and `Config.method` is now a property derived
  from `SPATIAL_SCHEME` (single source of truth).
- `Runner.sweep()` resolves the kernel once and `calculo_flujo()`
  reconstructs the cell averages with `cell_average()`.
- Each run result includes `spatial_scheme`.
- `nts-1d-run` prints the configuration source and run name under the
  `--- STARTING CALCULATION ---` banner, e.g.
  `Source: outputs/inputs/inputs.py | run config_dict_003`.
- The manual-run summary and confirmation prompts are now in English
  (`--- CONFIGURATION SUMMARY ---`, `Run? (y/n) [y]:`).

### Notes
- DD is bit-for-bit identical to the previous version.
- STEP is first order; at 100 cells it sits ~0.9% below DD (expected
  behaviour of the step approximation).
- No clipping or positivity constraints: DD's negative fluxes in thick
  cells are reported as-is.

## [2.8.0] - 2026-11-02 - English outputs and bilingual documentation

### Changed
- All generated figures, reports and CLI prompts/messages are in English.
- Translated `plot_1d_flux`, `sweep_kpis`, solver console messages, the
  config generator and `nts-1d-data` output.
- Main documentation now has English versions; Spanish versions are kept.

### Added
- `doc/MULTIPLICATIVE_MEDIA_EN.md` (English version).
- `doc/desc_EN.md` (English version).
- `Changelog_EN.md` updated with the 2.x entries.
- Project version 2.8.0.

## [2.7.0] - 2026-11-02 - Spatial placeholders

### Added
- `nts-1d-config` accepts placeholders for `NC` and `HR`.
- `Config.auto_input` validates positive integer `NC`/`IZL` and positive
  finite `HR`.

### Changed
- `NC` placeholders must expand to positive integers; `N`, `IZL` and
  `MAX_OUTER` remain numeric.

## [2.6.0] - 2026-11-02 - `nts-1d-config` command

### Changed
- The 1D config generator entry point is now `nts-1d-config`.

## [2.5.0] - 2026-11-02 - `nts-test` entry point

### Added
- `nts-test` runs the unittest suite with `-v`, `--failfast`, `-p` and
  `--start-dir`.

## [2.4.0] - 2026-11-02 - 1D config generator with placeholders

### Added
- Interactive config generator with `kk`/`mm` placeholders.
- `nts-generate --json` expansion to `.json` or `.py`.
- `Config.as_dict()` and embedded run configuration.

### Fixed
- Placeholder expansion no longer rounds `TOL_K` or other config floats.

## [2.3.0] - 2026-11-01 - 1D flux plots

### Added
- `nts-1d-plot -r` for scalar flux, angular flux per direction and
  `k_history`.
- Run selection with `--run` / `--list-runs`.

## [2.2.0] - 2026-11-01 - Manual and JSON 1D configuration

### Added
- `nts-1d-run --manual` interactive wizard.
- `nts-1d-run --json` file loading.
- Effective configuration embedded in the output.

## [2.1.0] - 2026-11-01 - Multiplicative media and `k_eff`

### Added
- `NU_SIGF` and `MODE` (`fixed_source`, `eigenvalue`, `fixed_k`, `driven`).
- Power iteration for `k_eff`, global balance and optional power
  normalization.
- `nts-1d-data` / `nts-1d-plot` support for the new fields.

## [2.0.0] - 2026-09-14 - Documentation and consistency

### Changed
- README rewritten in English with the full command reference.
- Version aligned to 2.0.0.

## [1.3.0] - 2026-05-26 - MFLUX Plotting and CLI Packaging

### Added
- New `plot` CLI command to render a 2D MFLUX heatmap with a colorbar
- Plots directory `outputs/results/plots/` with automatic image numbering
- `matplotlib` dependency for chart generation

### Changed
- Packaging configuration with `build-system` and `tool.uv.package` to enable entry points
- Explicit setuptools package/module inclusion
- `run` results are now saved as `output_*.json`

### Fixed
- `nts` entry point now works with `uv run nts ...`

---

## [1.3.1] - 2026-06-01 - 1D CLI and Placeholders

### Added
- `run-1d` CLI command to execute `NTS_DD_1D` and write consolidated JSON outputs
- `generate --place-holder` to build `outputs/inputs/inputs.py` from `inputs_placeholder.py`
- `utils/plot_scs_flux.py` to plot SCS vs scalar flux (positions 0 and 99)
- `utils/extract_1d_flux.py` to extract scalar flux values into `datos.json`
- Shortcuts: `nts-1d-data`, `nts-1d-plot`, `nts-1d-run`, `nts-generate`

### Changed
- 1D outputs now use `output_1d_###.json`

---

## [1.2.0] - 2026-03-30 - Update and Refinement

### Added
- Explicit defaults in CLI argument help
- Complete .gitignore for generated files
- .gitkeep files to preserve directory structure

### Changed
- `json` imports moved to the top of config.py
- Argument help now displays default values

### Improved
- Documentation updated with all changes
- Cleaner, more maintainable code

---

## [1.1.0] - 2026-03-30 - Post-Implementation Fixes

### Removed
- **Full TUI removed** - System is now CLI-only
- **Output parser removed** - Solvers produce JSON directly

### Changed
- **Less verbose logging** - Console WARNING level, file DEBUG level
- **Solver execution fixed** - From stdin to argument: `NTS_DD input.txt`
- Simplified `main.py` (no TUI router)
- Simplified `cmd_show` to read JSON directly

### Fixed
- Solvers now produce valid JSON outputs (~890KB)
- No unnecessary INFO messages in console
- Correct execution: `subprocess.run([solver_path, input_path])`

### Documentation
- README.md updated without TUI
- QUICKSTART.md simplified (CLI only)
- IMPLEMENTATION_SUMMARY.md updated with current architecture
- FIXES_APPLIED.md with correction log

---

## [1.0.0] - 2026-03-30 - Initial Implementation

### Added
- Complete NTS automation system
- Core modules: config.py, validator.py, input_builder.py
- Execution: runner.py, parallel.py, output_parser.py (later removed)
- CLI: 6 commands (status, validate, generate, run, list, show)
- TUI: 4 screens + widgets (later removed)
- Utils: logger.py, paths.py
- Templates: base_input.json
- Full documentation

### Features
- Input.txt generation with strict physical validation
- Robust validation (even N, σ_s < σ_t, ranges, dimensions)
- Parallel execution with multiprocessing
- 4 supported solvers: NTS_DD, NTS_LD, NTS_RM_CN, NTS_RM_LLN
- Full logging with metrics
- Centralized path system

### Tests
- 23/23 tasks completed
- Inputs generated successfully
- All CLI commands working
- Solvers detected correctly

---

## Version Notes

### v1.3.0 - MFLUX Plotting
Adds the CLI plot command and packages the project so entry points work.

### v1.2.0 - Refinement
Small code-quality and documentation improvements.

### v1.1.0 - Critical Fixes
TUI and output parser removal for a simpler system, plus solver execution fix.

### v1.0.0 - Complete MVP
First functional release with all major features implemented.

---

## Format

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Change Types
- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features to be removed later
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security patches
