# Quick Reference - NTS Automation System

## 🚀 Start

```bash
uv run python main.py [command]
```

## 📝 CLI Commands

### System Status
```bash
uv run python main.py status
```

### Validate Configuration
```bash
uv run python main.py validate <config.json>
```

### Generate Input File
```bash
uv run python main.py generate <config.json> [--preview] [-o output.txt]
```

### List Files
```bash
uv run python main.py list inputs   # List input files
uv run python main.py list outputs  # List output files
```

### Run Simulations
```bash
uv run python main.py run --solver <SOLVER> [--parallel <N>] [-i input1.txt ...]

# Examples:
uv run python main.py run --solver NTS_DD --parallel 4
uv run python main.py run --solver NTS_LD -i outputs/inputs/input_001.txt
```

### Show Results
```bash
cat outputs/results/output_001.txt
```

## 🎯 Available Solvers

- `NTS_DD` - Diamond Difference
- `NTS_LD` - Linear Discontinuous
- `NTS_RM_CN` - Response Matrix CN
- `NTS_RM_LLN` - Response Matrix LLN

## 📋 Configuration Format

```json
{
  "N": 4,              // Number of discrete ordinates (even)
  "NZ": 1,             // Number of material zones
  "zones": [
    {
      "sigma_t": 0.5,  // Total cross-section
      "sigma_s": 0.3   // Scattering cross-section (must be < sigma_t)
    }
  ],
  "NR_X": 2,           // Number of X regions
  "XDOM": [            // X domain definition
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "NR_Y": 2,           // Number of Y regions
  "YDOM": [            // Y domain definition
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "ZMAP": [[1, 1], [1, 1]],            // Zone map (NR_Y x NR_X)
  "QMAP": [[1.0, 1.0], [1.0, 1.0]],    // Source map (NR_Y x NR_X)
  "BC": [0.0, 0.0, 0.0, 0.0],          // Boundary conditions [L,R,B,T]
  "TOL": 1e-5                          // Convergence tolerance
}
```

## 📁 File Locations

```
outputs/
├── inputs/        # Generated input files (input_XXX.txt)
├── results/       # Simulation results (output_XXX.txt - JSON format)
└── logs/          # Log files
```

## 📊 Output Format

Results are JSON files with:
- `STATUS`: Status code (0 = success)
- `ITER`: Number of iterations
- `CPU`: CPU time
- `MFLUX`: Mean flux matrix
- `MFLOW`: Directional flow matrices

## ⚡ Quick Workflow

```bash
# 1. Validate config
uv run python main.py validate templates/base_input.json

# 2. Generate input
uv run python main.py generate templates/base_input.json

# 3. Run simulation
uv run python main.py run --solver NTS_DD

# 4. View results
cat outputs/results/output_001.txt
```

## 📚 More Help

```bash
uv run python main.py --help
uv run python main.py [command] --help
```
