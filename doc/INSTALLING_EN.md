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

The CLI and TUI write into `outputs/` in the current directory. Choose another
work directory with:

```bash
export NTS_HOME="$HOME/nts-work"     # Linux/macOS
set NTS_HOME=%USERPROFILE%\nts-work  # Windows cmd
```

Create a 1D configuration:

```bash
nts-1d-config -o outputs/inputs/config_1d_001.json
```

Run it:

```bash
nts-1d-run --json outputs/inputs/config_1d_001.json
```

Open the TUI:

```bash
nts-tui
```

The TUI can create configurations, run the 1D solver, inspect results, generate
plots, build sweeps and export data.

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

The PyPI wheel does not contain:

- `NTS_DD`
- `NTS_LD`
- `NTS_STEP`
- `NTS_RM_CN`
- `NTS_RM_LLN`
- the `.c` / `.h` sources

For the 2D workflow:

1. Clone the repository.
2. Compile the binaries under `solvers/runners/`.
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
| `nts run` says solver missing | Compile 2D binaries and set `NTS_SOLVERS_DIR` |
| `nts-test` does not exist | It is development-only; use `uv run python -m cli.run_tests` |
| `outputs/` appears elsewhere | Set `NTS_HOME` or run from the desired work directory |
