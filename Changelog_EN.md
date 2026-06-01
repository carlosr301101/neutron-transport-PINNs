# Changelog

Record of all notable changes in the NTS Automation System project.

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
