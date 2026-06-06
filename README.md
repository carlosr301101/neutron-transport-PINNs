# NTS Automation System

Version: 1.3.1

CLI automation system for neutron transport (NTS) simulations with parallel execution, robust configuration management, Python 1D solver, and post-processing tools.

## 🚀 Features

- ✅ **Automatic input.txt generation** with strict physical validation
- ✅ **Complete CLI** for batch operations and scripting
- ✅ **Parallel execution** of multiple simulations
- ✅ **Robust configuration validation** before running
- ✅ **Direct JSON outputs** from solvers (no extra parsing)
- ✅ **Logging system** with metrics and detailed logs
- ✅ **Multiple solver management** (NTS_DD, NTS_LD, NTS_RM_CN, NTS_RM_LLN)
- ✅ **Python 1D solver** (`NTS_DD_1D`) with Diamond Difference
- ✅ **Placeholder generation** for parametric sweeps
- ✅ **CLI shortcuts** for 1D workflows
- ✅ **Post-processing**: data extraction and automatic plotting

## 📋 Requirements

- Python 3.14+
- uv (package manager)
- Compiled NTS binaries in `solvers/runners/` (for 2D solver)
- Python 1D solver bundled in `solvers/runners/NTS_DD_1D.py`

## 🔧 Installation

```bash
# Install dependencies with uv
uv sync

# Verify installation
uv run nts status
```

## 🎯 Usage

### Available Commands

#### 1. View system status
```bash
uv run nts status
```

#### 2. Validate configuration
```bash
uv run nts validate templates/base_input.json
```

#### 3. Generate input.txt
```bash
# Generate from JSON configuration
uv run nts generate templates/base_input.json

# With preview
uv run nts generate templates/base_input.json --preview
```

#### 3.1 Generate inputs with placeholders (parametric sweep)
```bash
# Reads outputs/inputs/inputs_placeholder.py and writes outputs/inputs/inputs.py
uv run nts-generate --place-holder KK 0.1 0.95 0.05

# Multiple placeholders in parallel
uv run nts-generate --place-holder KK 0.1 0.95 0.05 --place-holder QQ 1 3 1
```

**Example `inputs_placeholder.py`:**
```python
config_dict = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [100],
    "HR": [100],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [kk],   # placeholder
    "Q": [0],
    "N": 4,
}
```

The result is `outputs/inputs/inputs.py` with `config_dict_001`, `config_dict_002`, etc.

#### 4. List files
```bash
# List generated inputs
uv run nts list inputs

# List results
uv run nts list outputs
```

#### 5. Run 2D simulations (binaries)
```bash
# Run with a specific solver
uv run nts run --solver NTS_DD

# Run specific inputs
uv run nts run -i outputs/inputs/input_001.txt

# Run in parallel (4 processes)
uv run nts run --solver NTS_DD --parallel 4
```

#### 6. Run 1D solver (Python)
```bash
# Runs all configs in outputs/inputs/inputs.py
uv run nts-1d-run
# or
uv run nts run-1d
```

Generates a consolidated JSON in `outputs/results/output_1d_###.json` with `scalar_flux` and metadata per config.

#### 7. View results
```bash
# View 2D solver output file
cat outputs/results/output_001.json

# Output is JSON with STATUS, ITER, MFLUX, MFLOW, etc.
```

#### 8. Plot MFLUX
```bash
uv run nts plot
uv run nts plot --result outputs/results/output_002.json --show
```

### ⚡ Shortcuts (entry points)

| Shortcut | Description |
|----------|-------------|
| `nts-1d-data` | Extract scalar flux values into `datos.json` from 1D outputs |
| `nts-1d-plot` | Plot SCS vs scalar flux (positions 0 and 99) |
| `nts-1d-run` | Run the 1D solver for the configs in `inputs.py` |
| `nts-generate` | Generate `inputs.py` from `inputs_placeholder.py` |

**Usage:**
```bash
uv run nts-1d-data --latest
uv run nts-1d-data --latest --positions 0 50 99
uv run nts-1d-plot
uv run nts-1d-run
uv run nts-generate --place-holder KK 0.1 0.95 0.05
```

## 📈 Post-processing

### Extract data
```bash
uv run nts-1d-data --latest
```

Generates `outputs/results/datos.json` with `SCS` and `scalar_flux` at configurable positions.

### Plot SCS vs Flux
```bash
uv run nts-1d-plot
```

Generates PNG in `outputs/results/plots/scs_flux.png` with two subplots (position 0 and position 99).

## 📁 Project Structure

```
neutron-transport-PINNs/
├── main.py                      # CLI entry point
├── cli/                         # CLI interface
│   ├── commands.py             # Main commands
│   ├── run_1d.py               # Entry point: nts-1d-run
│   └── generate_placeholder.py # Entry point: nts-generate
├── core/                        # Generation and validation
├── execution/                   # Solver execution
├── utils/                       # Utilities
│   ├── paths.py
│   ├── logger.py
│   ├── plot_scs_flux.py        # Plot SCS vs flux
│   └── extract_1d_flux.py      # Extract 1D data
├── templates/                   # Configuration templates
├── outputs/                     # System outputs (gitignored)
│   ├── inputs/                 # input_XXX.txt files, inputs.py
│   ├── results/                # output_*.json files, datos.json
│   └── logs/                   # Simulation logs
└── solvers/
    └── runners/                # NTS binaries + Python 1D solver
        ├── NTS_DD_1D.py
        └── cuadraturas.py
```

## 📝 Configuration Format

See `templates/base_input.json` for a complete example with comments.

Main parameters:
- **N**: Discrete ordinates (even)
- **NZ**: Number of zones
- **zones**: Cross sections (σ_s < σ_t)
- **XDOM, YDOM**: Domain geometry
- **ZMAP**: Material map
- **QMAP**: Source map
- **BC**: Boundary conditions
- **TOL**: Convergence tolerance

### 1D format (Python solver)

For `NTS_DD_1D`, configs use a simplified format:
- `num_regions`, `num_zones`
- `NC`: cells per region
- `HR`: thicknesses
- `IZL`: zone for each region
- `SCT`: total sigma per zone
- `SCS`: scattering sigma per zone
- `Q`: source per region
- `N`: quadrature order
- `reflex_izq`, `reflex_der`: reflective conditions
- `bound_left`, `bound_right`: boundary conditions

## 📊 Output Format

### 2D solver (C binaries)
```json
{
  "STATUS": 0,
  "ITER": 20,
  "CPU": -0.999,
  "MFLUX": [[...], [...]],
  "MFLOW": [[[...]], [[...]]]
}
```

### 1D solver (Python)
```json
{
  "solver": "NTS_DD_1D",
  "runs": [
    {
      "config_name": "config_dict_001",
      "scalar_flux": [...],
      "iteration": 13,
      "converged": true,
      "timestamp": "2026-06-01T19:02:59"
    }
  ]
}
```

## 🔄 Typical Workflow

### 2D solver
1. **Create/edit** configuration in JSON
2. **Validate** configuration
3. **Generate** input.txt files
4. **Run** simulations in parallel
5. **Analyze** JSON results

### 1D solver
1. **Create/edit** `outputs/inputs/inputs_placeholder.py` with placeholders
2. **Generate** variants with `uv run nts-generate --place-holder ...`
3. **Run** with `uv run nts-1d-run`
4. **Extract data** with `uv run nts-1d-data --latest`
5. **Visualize** with `uv run nts-1d-plot`

## 🐛 Troubleshooting

```bash
# Check available solvers
uv run nts status

# View detailed logs
cat outputs/logs/nts_automation_*.log

# Verify the 1D solver produces results
uv run nts-1d-run

# Regenerate inputs from placeholders
uv run nts-generate --place-holder KK 0.1 0.95 0.05
```

## 📚 Help

```bash
# General help
uv run nts --help

# Specific command help
uv run nts [command] --help
```

## 📂 Repository Management

### Ignored Files

The `.gitignore` is configured to ignore generated files:

- ✅ **Generated outputs**: `outputs/inputs/*.txt`, `outputs/results/*.json`, `outputs/logs/*.log`
- ✅ **Regenerable placeholders**: `outputs/inputs/inputs.py`, `inputs_placeholder.py`
- ✅ **1D solver outputs**: `resultados_runner_*.xlsx`, `Config.log`
- ✅ **Python cache**: `__pycache__/`, `*.pyc`
- ✅ **Virtual environments**: `.venv/`, `venv/`
- ✅ **IDE files**: `.vscode/`, `.idea/`
- ✅ **Temporary files**: `*.tmp`, `*.bak`, `Notas.md`

The directory structure is preserved with `.gitkeep` files in `outputs/`.

---

**NTS Automation System** - Neutron transport simulation automation 🚀
