# Quickstart — NTS Automation System

One-page cheatsheet. Full reference: [README](../README.md).

All commands use the `nts` entry point (see `pyproject.toml`):

```bash
uv run nts [command]        # main CLI
uv run nts-1d-run           # shortcuts
uv run nts-generate
uv run nts-1d-data --latest
uv run nts-1d-plot
```

## 🚀 First Steps

```bash
# 1. Install dependencies
uv sync

# 2. Check system status (solvers, files)
uv run nts status

# 3. List available commands
uv run nts --help
```

## 🧠 Command Cheatsheet

```bash
uv run nts status                       # System overview
uv run nts validate <config.json>       # Validate JSON config (Pydantic)
uv run nts generate <config.json>       # Generate input_###.txt
uv run nts generate <config.json> -p    # Preview the 11-line input
uv run nts list inputs | outputs        # List generated files
uv run nts show <output_###.json>       # Show result summary
uv run nts run -s NTS_DD -p 4           # Run all inputs, 4 processes
uv run nts plot -r <output_###.json>    # Plot MFLUX heatmap
uv run nts run-1d                       # Run the Python 1D solver
```

## 🎯 Available Solvers

2D (C binaries in `solvers/runners/`):

- `NTS_DD` — Domain Decomposition
- `NTS_LD` — Line Diffusion (fastest)
- `NTS_STEP` — Characteristic STEP sweeps (beam sources)
- `NTS_RM_CN` — Response Matrix + Crank-Nicolson (most precise)
- `NTS_RM_LLN` — Response Matrix + Linear Lattice (assemblies)

1D (Python, `solvers/runners/NTS_DD_1D.py`): Diamond Difference SN solver.

## 📝 Configuration Format (2D)

```json
{
  "N": 4,
  "NZ": 1,
  "zones": [
    {
      "sigma_t": 0.5,
      "sigma_s": 0.3
    }
  ],
  "NR_X": 2,
  "XDOM": [
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "NR_Y": 2,
  "YDOM": [
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "ZMAP": [[1, 1], [1, 1]],
  "QMAP": [[1.0, 1.0], [1.0, 1.0]],
  "BC": [0.0, 0.0, 0.0, 0.0],
  "TOL": 1e-5
}
```

Notes:

- `BC` order is **[left, right, bottom, top]**; `0.0` = vacuum, `1.0` = reflective.
- Constraints: `N` even, `sigma_s < sigma_t`, `ZMAP` values in `[1, NZ]`, `TOL ∈ [1e-7, 1e-2]`.

## ⚡ Quick Workflow — 2D

```bash
# 1. Validate config
uv run nts validate example_config.json

# 2. Generate input
uv run nts generate example_config.json

# 3. Run (all inputs, parallel)
uv run nts run --solver NTS_DD --parallel 4

# 4. Inspect and plot
uv run nts show outputs/results/output_001.json
uv run nts plot -r outputs/results/output_001.json
```

## ⚡ Quick Workflow — 1D (parametric sweep)

```bash
# 1. Edit outputs/inputs/inputs_placeholder.py using a bare placeholder,
#    e.g. "SCS": [kk]
# 2. Expand placeholders (arithmetic range 0.1 → 0.95 step 0.05)
uv run nts-generate --place-holder kk 0.1 0.95 0.05

# 3. Run the 1D solver over every generated config
uv run nts-1d-run

# 4. Extract the scalar flux at selected positions
uv run nts-1d-data --latest --positions 0 50 100

# 5. Plot SCS vs flux
uv run nts-1d-plot
```

## 📁 File Locations

```
outputs/
├── inputs/    # input_###.txt (2D), inputs.py + inputs_placeholder.py (1D)
├── results/   # output_###.json (2D), output_1d_###.json (1D), datos.json, plots/
└── logs/      # nts_automation_*.log, simulation_*.log
```

## 📚 More Help

```bash
uv run nts --help
uv run nts <command> --help
```
