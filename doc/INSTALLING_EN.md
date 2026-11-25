# Installation

Guide for installing `neutron-transport-pinns` from PyPI, from a local wheel,
or from the repository.

> The PyPI package contains the CLI, the TUI and the Python 1D solver.
> The 2D C solvers are not included in the wheel. Clone the repository and
> compile the binaries to use the 2D workflow.

## Requirements

- Python **3.14 or newer**.
- One of:
  - [uv](https://docs.astral.sh/uv/) (recommended),
  - `pip`.
- Linux, macOS or Windows.

Check Python:

```bash
python --version
```

## Install with uv

### One-off command

```bash
uvx --from neutron-transport-pinns nts --help
uvx --from neutron-transport-pinns nts-tui
```

### Permanent install

```bash
uv tool install neutron-transport-pinns
```

Verify:

```bash
nts --help
nts status
nts-tui
```

Upgrade:

```bash
uv tool upgrade neutron-transport-pinns
```

Uninstall:

```bash
uv tool uninstall neutron-transport-pinns
```

### Inline images in the TUI

Inline preview is optional:

```bash
uv tool install "neutron-transport-pinns[images]"
```

It requires Kitty, WezTerm, iTerm2 or sixel support. Without it, the TUI saves
the PNG and offers to open it externally.

## Install with pip

```bash
python -m pip install neutron-transport-pinns
```

With inline images:

```bash
python -m pip install "neutron-transport-pinns[images]"
```

Verify:

```bash
nts --help
nts status
nts-tui
```

Upgrade:

```bash
python -m pip install --upgrade neutron-transport-pinns
```

Uninstall:

```bash
python -m pip uninstall neutron-transport-pinns
```

On Windows, if `python` is not 3.14:

```powershell
py -3.14 -m pip install neutron-transport-pinns
```

## First run

Create a work directory and a small 1D eigenvalue problem:

```bash
mkdir nts-demo
cd nts-demo
cat > quickstart.json <<'JSON'
{
  "num_regions": 1,
  "num_zones": 1,
  "NC": [20],
  "HR": [20.0],
  "IZL": [1],
  "SCT": [1.0],
  "SCS": [0.9],
  "NU_SIGF": [0.11],
  "Q": [0.0],
  "N": 8,
  "SPATIAL_SCHEME": "DD",
  "reflex_izq": false,
  "reflex_der": false,
  "bound_left": [0, 0, 0, 0],
  "bound_right": [0, 0, 0, 0],
  "MODE": "eigenvalue",
  "TOL_K": 1e-6,
  "MAX_OUTER": 200
}
JSON

nts-1d-run --json quickstart.json -o outputs/results/quickstart.json
```

The solver prints convergence information and writes a consolidated JSON.
Inspect it and generate a plot:

```bash
nts-1d-plot -r outputs/results/quickstart.json --kind k-history
```

Default plot:

```text
outputs/results/plots/k_history.png
```

For this quickstart, the expected eigenvalue is approximately:

```text
k_eff ~= 1.0264
```

To use another work directory:

```bash
export NTS_HOME="$HOME/nts-work"     # Linux/macOS
set NTS_HOME=%USERPROFILE%\nts-work  # Windows cmd
```

The CLI and TUI create `outputs/` inside `NTS_HOME`, not inside
`site-packages`.

### Start the TUI

```bash
nts-tui
```

Typical workflow:

1. **Config**: geometry, materials, mode, source and boundaries.
2. **Save**: write `outputs/inputs/config_1d_###.json`.
3. **Run**: execute the 1D solver with a live log.
4. **Results**: inspect `k_eff`, iterations and convergence.
5. **Plots**: scalar, angular, `k_history` or SCS.
6. **Placeholders/Export**: parametric sweeps, `datos.json`, Excel.

Quit with `q`. If the command is not on `PATH`:

```bash
python -m tui.app
```

### Expected first-run output

- `nts status` may warn that the 2D binaries are missing. This is normal for
  the PyPI wheel; the 1D solver and TUI are fully functional.
- `nts-1d-run` writes `outputs/results/quickstart.json`.
- `nts-1d-plot` writes `outputs/results/plots/k_history.png`.
- The TUI writes configs under `outputs/inputs/` and results under
  `outputs/results/`.

### Windows console

On Windows the CLI prints ASCII output so legacy PowerShell code pages
(`cp1252`/`cp850`) cannot break it. The final checkmark is printed as `OK`:

```text
OK Completed 3 run(s). Output: outputs/results/output_1d_003.json
```

To restore the Unicode glyphs (`✓`, `✗`, `•`) in a modern terminal:

```powershell
chcp 65001
$env:NTS_UNICODE = "1"
```

To force ASCII on any system:

```powershell
$env:NTS_ASCII = "1"
```

The TUI is not affected: Textual writes through its own driver.

## Install from a local wheel

```bash
uv build --clear
uv pip install dist/*.whl
```

Or with pip:

```bash
python -m pip install dist/*.whl
```

## Development install

```bash
git clone https://github.com/carlosr301101/neutron-transport-PINNs.git
cd neutron-transport-PINNs
uv sync
```

With inline images:

```bash
uv sync --extra images
```

Development commands:

```bash
uv run nts --help
uv run nts-tui
uv run python -m cli.run_tests
uv run python -m cli.run_tests -v
```

`nts-test` is a repository-only development command and is not included in the
published wheel.

## 2D solvers

The **Linux x86_64** and **Windows amd64** wheels include:

- `NTS_DD`
- `NTS_LD`
- `NTS_STEP`
- `NTS_RM_CN`
- `NTS_RM_LLN`

No compilation is needed on those platforms; `nts status` must list all five
as OK. The sdist (macOS, ARM, and other platforms) ships the `.c` sources and
the build helpers but not the binaries. For those platforms:

1. Clone the repository.
2. Compile the binaries under `solvers/runners/` with `make -C solvers rebuild`
   (Linux) or `solvers/build_windows.ps1` (Windows).
3. Point to them if they are outside the repository layout:

```bash
export NTS_SOLVERS_DIR="$HOME/nts-solvers"  # Linux/macOS
set NTS_SOLVERS_DIR=%USERPROFILE%\nts-solvers  # Windows cmd
```

`nts status` reports missing binaries.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python: command not found` | Install Python 3.14 or use `py -3.14` on Windows |
| `nts: command not found` | Run `uv tool install` or `pip install`, then check `PATH` |
| `nts-tui` does not open | Use a terminal supported by Textual |
| Inline preview is missing | Install `[images]` and use Kitty/WezTerm/iTerm2/sixel |
| `nts run` says solver missing | On Linux x86_64/Windows amd64 reinstall the wheel; otherwise compile the 2D binaries and set `NTS_SOLVERS_DIR` |
| `nts-test` does not exist | It is development-only; use `uv run python -m cli.run_tests` |
| `outputs/` appears elsewhere | Set `NTS_HOME` or run from the desired work directory |
