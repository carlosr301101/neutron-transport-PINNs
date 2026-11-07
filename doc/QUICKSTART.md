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
uv run nts-test                         # Run the unittest suite
uv run nts-test -v                      # Verbose tests
```

## 🎯 Available Solvers

2D (C binaries in `solvers/runners/`):

- `NTS_DD` — Domain Decomposition
- `NTS_LD` — Line Diffusion (fastest)
- `NTS_STEP` — Characteristic STEP sweeps (beam sources)
- `NTS_RM_CN` — Response Matrix + Crank-Nicolson (most precise)
- `NTS_RM_LLN` — Response Matrix + Linear Lattice (assemblies)

1D (Python, `NTS_DD_1D.py` / `NTS_STEP_1D.py` / `NTS_SC_1D.py`): S_N solver
with selectable DD / STEP / SC discretization over a shared engine
(`config.py` + `runner.py`).

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

### Generate a config JSON (with placeholders)

```bash
# Interactive generator; -o is optional (auto-numbered)
uv run nts-1d-config -o outputs/inputs/config_1d_001.json

# In float fields you may type kk/mm instead of a number.
uv run nts-generate --json outputs/inputs/config_1d_001.json \
  --place-holder kk 0.1 0.95 0.05 \
  --place-holder mm 0.05 0.20 0.05 \
  -o outputs/inputs/inputs_1d.json

uv run nts-1d-run --json outputs/inputs/inputs_1d.json
```

- `-o .py` writes `inputs.py`; `-o .json` writes a list.
- Placeholders are combined in parallel by index.
- `NC` and `HR` also accept placeholders; `NC` must expand to positive
  integers. `N`, `IZL` and `MAX_OUTER` stay numeric.

### Manual or JSON configuration

```bash
# Interactive step-by-step wizard (one run)
uv run nts-1d-run --manual

# One JSON object or a list of objects
uv run nts-1d-run --json config.json

# Also write a formatted Excel workbook next to the JSON
uv run nts-1d-run --json config.json --excel

# Convert an existing output
uv run nts-1d-excel outputs/results/output_1d_003.json -o results.xlsx
```

`--manual`, `--json` and `-c` are mutually exclusive. The wizard prints a
configuration summary and asks `Run? (y/n) [y]:` before running. Each run
prints where it came from:

```text
--- STARTING CALCULATION ---
Source: outputs/inputs/inputs.py | run config_dict_003
```

`nts-1d-data` uses the `configuration` embedded in the output, so it also
works for manual/JSON runs.

### Plotting 1D results

```bash
# List the runs in a raw output
uv run nts-1d-plot -r outputs/results/output_1d_016.json --list-runs

# Scalar flux vs x
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind scalar --run manual

# Angular flux: one colored line per direction, one legend
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual

# k_eff history (eigenvalue only)
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind k-history --run manual

# Legacy datos.json mode
uv run nts-1d-plot -i outputs/results/datos.json --x k_eff
```

If the file has more than one run, `--run NAME|INDEX` is required. Use
`--run all` to overlay all runs for `scalar`/`k-history`; `angular` takes
exactly one run.

## ⚛️ Multiplicative Media (1D, k_eff)

The Python 1D solver supports fission and `k_eff` through `NU_SIGF` and
`MODE`. The 2D C solvers remain fixed-source only.

```python
# outputs/inputs/inputs.py — 20 cm homogeneous slab, vacuum, S8
config_dict = {
    "num_regions": 1, "num_zones": 1,
    "NC": [100], "HR": [20.0], "IZL": [1],
    "SCT": [1.0], "SCS": [0.9],
    "NU_SIGF": [0.11],          # nu*Sigma_f [cm^-1]
    "Q": [0.0], "N": 8,
    "reflex_izq": False, "reflex_der": False,
    "bound_left": [0, 0, 0, 0], "bound_right": [0, 0, 0, 0],
    "MODE": "eigenvalue",       # compute k_eff
}
```

```bash
uv run nts-1d-run
uv run nts-1d-data --latest --positions 0 50 100
uv run nts-1d-plot --x k_eff
```

Expected S8 result: `k_eff ≈ 1.02668` (`k_inf = 1.1`).

| `MODE` | What it does |
|---|---|
| `fixed_source` | No fission (historical mode) |
| `eigenvalue` | Homogeneous problem, computes `k_eff` (`Q=0`) |
| `fixed_k` | Imposes `k`; with a source it is driven, without it a mode shape |
| `driven` | Physical source + fission (`k=1`); requires `Q` or incoming flux |

Optional power normalization:

```python
"POWER_KW": 10.0, "E_F_MEV": 200.0, "NU": 2.4, "AREA_CM2": 1.0,
```

Full reference: [MULTIPLICATIVE_MEDIA_EN.md](MULTIPLICATIVE_MEDIA_EN.md).

## 🧩 Spatial Schemes (1D)

The 1D solver can use three interchangeable cell schemes:

```python
"SPATIAL_SCHEME": "DD",   # "DD" (default) | "STEP" | "SC"
```

| Scheme | Order | Notes |
|---|---|---|
| `DD` | 2nd | Historical scheme; bit-for-bit backward compatible |
| `STEP` | 1st | Implicit upwind, unconditionally positive, diffusive |
| `SC` | 2nd | Step characteristics; closest to DD on coarse meshes |

The wizard (`nts-1d-run --manual`, `nts-1d-config`) asks
`Spatial scheme (DD / STEP / SC) [DD]:` right after the quadrature order.

Per-scheme entry points (same flags as `nts-1d-run`, but they force the
scheme and print a warning if the config says otherwise):

```bash
uv run nts-1d-run-dd   --json config.json
uv run nts-1d-run-step --json config.json
uv run nts-1d-run-sc   --json config.json
```

S8, 100 cells, 20 cm benchmark: `k_eff = 1.026676` (DD), `1.026054` (SC),
`1.017843` (STEP). The three schemes share source, quadrature, boundary
conditions and iteration. No clipping or positivity constraints are applied.

Full reference: [SPATIAL_SCHEMES_EN.md](SPATIAL_SCHEMES_EN.md).

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
