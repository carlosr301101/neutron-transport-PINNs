---
name: nts-pinns-autopilot
description: >-
  Operates the NTS Automation System (neutron-transport-PINNs, v3.10.0), a CLI/TUI for
  SN neutron transport simulations: generating/validating inputs, running the 2D
  C solvers (NTS_DD/LD/STEP/RM_CN/RM_LLN) and the Python 1D Diamond-Difference
  solver, launching parametric sweeps (placeholders to configs to runs to
  datos.json to plots), adding SN quadrature orders (N=2,4,6,8), extracting
  flux KPI tables, and solving 1D multiplicative media with fission and k_eff
  (MODE=eigenvalue|fixed_k|driven, NU_SIGF, power iteration, power
  normalization). Use this skill ANY time the user works in this repository,
  runs `uv run nts*` commands, or mentions kk/mm/SCT/SCS/NU_SIGF placeholders,
  k_eff, medio multiplicativo, eigenvalue, fixed_k, driven, nts-1d-config,
  inputs_placeholder.py, inputs.py, cuadraturas.py, output_1d_*.json, datos.json,
  N=4/N=6/N=8, nts tui, nts-tui, TUI, quadrature orders, or asks to
  run/compare/plot DD simulations, prepare KPI summaries, or guide the creation
  of a new neutron transport problem ("Quiero crear un problema de transporte
  de neutrones", "configurar un problema de transporte", "ayúdame a crear el
  config.json", "I want to set up a neutron transport problem", "help me build
  config.json") — even if they never name the system.
---

# NTS PINNs Autopilot

Operational knowledge for the NTS Automation System in this repository.
Full reference docs live in `README.md`, `doc/QUICKSTART.md` and
`doc/NTS_DOCUMENTATION.md` — read them when you need background theory or
solver method selection. This file is the short, operational path.

Installation: `doc/INSTALLING_EN.md`. Packaging and PyPI release:
`doc/PACKAGING_EN.md`.

## Installing and running

### End-user install from PyPI

With `uv`:

```bash
uv tool install neutron-transport-pinns
```

One-off without installing:

```bash
uvx --from neutron-transport-pinns nts --help
uvx --from neutron-transport-pinns nts-tui
```

With `pip`:

```bash
python -m pip install neutron-transport-pinns
```

Optional inline TUI image preview:

```bash
uv tool install "neutron-transport-pinns[images]"
# or
python -m pip install "neutron-transport-pinns[images]"
```

Requires Python 3.14+. On Windows use `py -3.14 -m pip ...` if needed.

Verify:

```bash
nts --help
nts status
nts-tui
```

`nts status` may report missing 2D binaries. That is expected for the PyPI
wheel; the 1D solver and TUI are included.

### Repository / agent install

Inside this checkout use `uv` for everything:

```bash
uv sync
uv sync --extra images       # optional inline preview
uv run nts --help
uv run nts-tui
uv run python -m cli.run_tests
```

Do not use bare `python3` inside the repo; use `uv run python` so the project
environment and dependencies are used.

### Running the tools

| Task | Installed package | Inside the repo |
|---|---|---|
| Main CLI | `nts` | `uv run nts` |
| TUI | `nts-tui` or `nts tui` | `uv run nts-tui` or `uv run nts tui` |
| 1D config wizard | `nts-1d-config` | `uv run nts-1d-config` |
| 1D solver | `nts-1d-run` | `uv run nts-1d-run` |
| Scalar/angular plots | `nts-1d-plot` | `uv run nts-1d-plot` |
| Extract `datos.json` | `nts-1d-data` | `uv run nts-1d-data` |
| Excel export | `nts-1d-excel` | `uv run nts-1d-excel` |
| Power normalization | `nts-1d-normalize` | `uv run nts-1d-normalize` |
| Placeholder expansion | `nts-generate` | `uv run nts-generate` |
| 2D solver | `nts run -s NTS_DD` | `uv run nts run -s NTS_DD` |

If a console script is not on `PATH`, use the module form:

```bash
python -m cli.main --help
python -m cli.main tui
python -m tui.app
python -m cli.run_1d --json config.json
python -m utils.extract_1d_flux --latest
python -m utils.plot_1d_flux -r outputs/results/output_1d_001.json
```

### Typical first 1D run

```bash
nts-1d-config -o outputs/inputs/config_1d_001.json
nts-1d-run --json outputs/inputs/config_1d_001.json \
  -o outputs/results/output_1d_001.json
nts-1d-plot -r outputs/results/output_1d_001.json --kind scalar
nts-tui
```

In the TUI: **Config → Save → Run → Results → Plots**. Quit with `q`.

### Runtime directories

- `NTS_HOME` changes the work root for `outputs/`:
  - Linux/macOS: `export NTS_HOME="$HOME/nts-work"`
  - Windows cmd: `set NTS_HOME=%USERPROFILE%\nts-work`
- `NTS_SOLVERS_DIR` points to compiled 2D binaries.
- The wheel does not include the 2D C binaries or sources. Clone the repo,
  compile them under `solvers/runners/`, or set `NTS_SOLVERS_DIR`.

## Guided setup of a new 1D problem

Trigger this workflow when the user wants to create or configure a new
problem, for example:

- ES: "Quiero crear un problema de transporte de neutrones", "configurar un
  problema de transporte", "ayúdame a crear el config.json", "nuevo caso 1D".
- EN: "I want to set up a neutron transport problem", "help me configure a
  neutron transport case", "build config.json", "create a new 1D problem".

Do not start it for questions about an existing config/run, or for 2D-only
work. If the intent is ambiguous, ask whether they want a new 1D config or to
run an existing one.

The goal is a validated `config_1d_*.json` for `nts-1d-run --json`, produced
by asking the user, not by guessing.

### Rules

- Ask in the user's language. Keep JSON keys and enum values exactly as shown
  (`MODE`, `NU_SIGF`, `SPATIAL_SCHEME`, ...).
- Ask in batches of 4-6 answers, with defaults in brackets. Do not dump the
  whole form at once.
- Never invent cross sections. If the user does not know a value, propose a
  default and label it as an assumption to confirm.
- Keep an accumulated table in the conversation and show it before writing.
- Validate with `tui.services.config_store.validate_config` (see below).
- Write `outputs/inputs/config_1d_<slug>.json` (or the path the user gives).
- Do not run the solver without confirmation.
- `nts-1d-config` is the fallback if the user prefers the terminal wizard;
  otherwise the agent collects the answers and writes the JSON.

### Questions to ask, in this order

**1. Geometry**

- Number of regions `num_regions` [1].
- Number of material zones `num_zones` [1]; must be `<= num_regions`.
- Per region: `NC` cells [1], `HR` thickness in cm [10.0], `IZL` zone [1].
  The three lists must have `num_regions` entries.

**2. Materials (per zone)**

- `SCT` = `Sigma_t` [1.0] cm^-1.
- `SCS` = `Sigma_s0` [0.9] cm^-1; it must satisfy `SCS <= SCT` (the 1D
  validator does not enforce this).
- `SIGMA_F` only when power normalization is requested; it must be `<= SCT`.
- Optional zone names for plots (`ZONE_NAMES`, one per zone). The terminal
  wizard does not ask for them; collect them here or in the TUI.

**3. Angular discretization**

- `N` in {2, 4, 6, 8} [8]. Other even orders fall back to S2 with a warning.
- `SPATIAL_SCHEME` in {`DD`, `STEP`, `SC`} [`DD`].

**4. Fission and mode**

Ask "Is the medium multiplying (fission)?"

- No: `MODE = fixed_source`, `NU_SIGF = 0` per zone.
- Yes: ask `NU_SIGF` per zone (= `nu*Sigma_f`, cm^-1; do **not** multiply by
  `4*pi`), then the intent:

| User intent | `MODE` | Requirements |
|---|---|---|
| Compute `k_eff` | `eigenvalue` | `NU_SIGF > 0`, `Q = 0`, zero incoming flux |
| Impose `k_eff` | `fixed_k` | `NU_SIGF > 0`, `K_EFF > 0` |
| Source-driven subcritical | `driven` | `NU_SIGF > 0`, `K_EFF = 1`, `Q` or incoming flux |

- `TOL_K` [1e-6], `MAX_OUTER` [200], `K0` [automatic; eigenvalue only].
- Power normalization optional: `POWER_KW`, `E_F_MEV` [200], `AREA_CM2` [1],
  and either `NU` [2.49] or `SIGMA_F` per zone. `POWER_KW` requires fission.

**5. Source**

- `Q` per region [0.0]; it must have `num_regions` entries.
- `eigenvalue` forces `Q = 0`; `fixed_source` and `driven` require `Q != 0`
  or a non-zero incoming flux.

**6. Boundaries**

- `reflex_izq`, `reflex_der` [false].
- `bound_left`, `bound_right`: one scalar expands to `N/2` equal values, or
  provide exactly `N/2` values.
- Reflective sides and `eigenvalue` use zero incoming flux.

**7. Convergence (optional)**

- `epsilon` [1e-5] relative flux tolerance.
- `max_iter` [2000].

**8. Placeholders (optional)**

If the user wants a sweep, numeric fields may be placeholder names (`kk`,
`mm`, ...): `SCS`, `NC` and `HR` accept them. `N`, `IZL` and `MAX_OUTER` must
stay numeric. Expand later with `nts-generate --json`.

### Minimal valid JSON

Fixed source, no fission:

```json
{
  "num_regions": 1,
  "num_zones": 1,
  "NC": [100],
  "HR": [10.0],
  "IZL": [1],
  "SCT": [1.0],
  "SCS": [0.9],
  "Q": [1.0],
  "N": 8,
  "SPATIAL_SCHEME": "DD",
  "MODE": "fixed_source",
  "NU_SIGF": [0.0],
  "reflex_izq": false,
  "reflex_der": false,
  "bound_left": [0.0],
  "bound_right": [0.0],
  "epsilon": 1e-5,
  "max_iter": 2000
}
```

Eigenvalue (the 20 cm quickstart):

```json
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
  "MODE": "eigenvalue",
  "TOL_K": 1e-6,
  "MAX_OUTER": 200,
  "reflex_izq": false,
  "reflex_der": false,
  "bound_left": [0.0],
  "bound_right": [0.0],
  "epsilon": 1e-5,
  "max_iter": 2000
}
```

Expected `k_eff ≈ 1.0264`.

### Validate before running

```bash
uv run python - <<'PY'
import json
import os
import tempfile
from pathlib import Path
from tui.services.config_store import validate_config

path = Path("outputs/inputs/config_1d_001.json").resolve()
cfg = json.loads(path.read_text())
with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)  # Config writes Config.log in the current directory
    errors, message = validate_config(cfg)
print(message)
for error in errors:
    print("ERROR:", error)
raise SystemExit(bool(errors))
PY
```

Then, only with confirmation:

```bash
uv run nts-1d-run --json outputs/inputs/config_1d_001.json
uv run nts-1d-plot -r outputs/results/output_1d_001.json --kind scalar
```

### Mistakes this workflow must prevent

- `Q` and `bound_*` lengths: `Q` has `num_regions` entries; `bound_*` has
  `N/2` (or one scalar).
- `SCT`/`SCS`/`NU_SIGF`/`SIGMA_F` have `num_zones` entries; `NC`/`HR`/`IZL`
  have `num_regions` entries.
- `SCS > SCT` is not rejected by the 1D validator: reject it in the dialogue.
- `NU_SIGF` is `nu*Sigma_f`; do not apply the spectral skill's `4*pi`.
- `eigenvalue` with `Q != 0` or incoming flux is rejected by design.
- `driven` forces `k = 1`; use `fixed_k` to scale fission.
- `fixed_k` with a source at `k = k*` is singular; do not combine them.
- Do not write the TUI-only `power_normalization` key to the JSON.

## Environment rules

- Inside this repository every command runs through `uv`: `uv run nts …`,
  `uv run python …`. The venv is Python 3.14 and only `uv run python` has the
  project deps (pandas, matplotlib, pydantic). Bare `python3` will fail on
  imports. For an installed PyPI package use the `nts*` entry points, not
  `uv run`.
- `outputs/` is gitignored: never commit anything inside it, and treat files
  there as regenerable except the curated `*_N*.json` datasets the sweep flow
  keeps (renamed by hand).
- The 2D solvers are compiled binaries in `solvers/runners/` (checked with
  `uv run nts status`, which lists all five: NTS_DD, NTS_LD, NTS_STEP,
  NTS_RM_CN, NTS_RM_LLN).
- Console output is ASCII on Windows because legacy PowerShell code pages
  (`cp1252`/`cp850`) cannot encode `✓`/`✗`; the CLI prints `OK`/`X` instead
  (for example `OK Completed 3 run(s).`). Set `NTS_UNICODE=1` (after
  `chcp 65001`) to keep the glyphs, or `NTS_ASCII=1` to force ASCII anywhere.

## Language

- Generated figures, reports, CLI prompts and solver messages are in
  **English**.
- Main documentation is in English. Spanish versions of
  `MULTIPLICATIVE_MEDIA.md` and `CHANGELOG.md` are kept beside the English
  versions.

## Running tests

```bash
uv run python -m cli.run_tests
uv run python -m cli.run_tests -v
uv run python -m cli.run_tests --failfast
uv run python -m cli.run_tests -p "test_plot_1d_flux.py"
```

## Command map

Main CLI (`cli/commands.py` via `main.py`):

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `nts tui` | Launch the 1D terminal UI (config, run, results, plots, placeholders, export) | — |
| `nts status` | Solver binaries + file counts | — |
| `nts validate <config.json>` | Pydantic validation + summary | — |
| `nts generate <config.json>` | JSON config → `input_###.txt` | `-p` preview, `--place-holder NAME START END STEP` (repeatable, nargs=4), `--json` placeholder config, `-o` output |
| `nts-1d-config` | Interactive 1D config JSON generator | `-o` output; `kk`/`mm` placeholders in float fields |
| `nts run` | 2D binaries (parallel) | `-s SOLVER`, `-i input.txt…`, `-p N` (default 4) |
| `nts run-1d` | Python 1D solver from file, JSON, or wizard | `-c` config path, `--json`, `--manual`, `-o` output path |
| `nts list inputs\|outputs` | Rich tables of generated files | — |
| `nts show <result.json>` | STATUS / ITER / CPU summary | — |
| `nts plot [-r result.json]` | MFLUX heatmap of a 2D JSON result | `-o` png path, `--show` |

Shortcuts (`pyproject.toml` scripts):

| Shortcut | Equivalent |
|----------|-----------|
| `nts-tui` | `nts tui` (same 1D terminal UI) |
| `nts-generate` | `nts generate` in placeholder mode (`--place-holder`, `--json`, `-o`) |
| `nts-1d-config` | Interactive 1D config JSON generator |
| `nts-1d-run` | `nts run-1d` (`-c`, `--json`, `--manual`); scheme from the config |
| `nts-1d-run-dd` | same flags, forces Diamond Difference |
| `nts-1d-run-step` | same flags, forces Step |
| `nts-1d-run-sc` | same flags, forces Step Characteristic |
| `nts-1d-data [--latest] [--positions 0 50 100]` | extract fluxes + embedded config → `datos.json` |
| `nts-1d-plot [-r output_1d.json \| -i datos.json] [--kind scalar\|angular\|k-history\|scs] [--run ...]` | scalar/angular flux, k_history, or legacy SCS plots |
| `nts-1d-excel output_1d_###.json [-o out.xlsx] [--run ...]` | export the consolidated JSON to a formatted workbook |
| `nts-1d-normalize output_1d_###.json --power-kw 10 [--nu 2.4]` | normalize an existing output to a target power |
| `python -m cli.run_tests [-v] [--failfast] [-p PATTERN]` | run the unittest suite |

## TUI (1D workflow)

Launch with `uv run nts tui` (same as `uv run nts-tui`).

- **Config**: geometry bar, editable region table (`cells`, `length`, `zone`,
  `Q`), zone table (`name`, `Sigma_t`, `Sigma_s0`), fission table (`nu*Sigma_f`,
  `Sigma_f`), plus every scalar field of the 1D config. Power normalization is
  a switch: `POWER_KW`, `E_F_MEV`, `NU` and `AREA_CM2` stay hidden until it is
  enabled, and an enabled switch with a blank `POWER_KW` is a form error.
  `Validate` runs in a worker (never block the UI with solver imports); the
  solver stack is warmed in the background when the pane mounts.
- **MODE rules**: `fixed_source` hides fission and stores `NU_SIGF=0`;
  `eigenvalue` hides `K_EFF` and forces `Q=0`; `fixed_k` requires `K_EFF`;
  `driven` uses `k=1`.
- **Boundaries**: a scalar expands to `N/2` directions (`0` with S8 becomes
  `[0,0,0,0]`); a full vector is kept. Reflective sides hide the field.
- **Run**: subprocess with live log and cancel; output JSON and Excel. Closing
  the TUI cancels a running solver.
- **Results/Plots**: per-run `k_eff`; scalar, angular, `k_history`, SCS.
  `Use in Plots` selects the file and switches to Plots (mounting it if its
  tab was never opened).
- **Placeholders/Export**: one `start:end:step` range per placeholder (e.g.
  `MM [10:20:1]`), preview, save JSON/Python, batch run and Cancel;
  `datos.json`, Excel and SCS plot live in Export.
- After every finished run all tabs refresh themselves (`refresh_all`);
  internal errors go to `outputs/logs/tui.log`.
- Optional inline preview: `uv sync --extra images`.

## Parametric sweep recipe (1D workflow)

The canonical loop, used to build the PINN training set. Example: sweep
scattering ratio kk from 0.1 to 0.95 with quadrature order N.

1. **Edit `outputs/inputs/inputs_placeholder.py`** — the placeholder appears
   as a bare variable name inside the dict, e.g. `"SCS": [kk]`.
2. **Expand**:
   ```bash
   uv run nts-generate --place-holder kk 0.1 0.95 0.05
   ```
   → `outputs/inputs/inputs.py` with `config_dict_001`, `config_dict_002`, …
   (inclusive range, floats rounded to the decimals of STEP; 0.1–0.95/0.05
   gives 18 configs).
3. **Run**:
   ```bash
   uv run nts-1d-run
   ```
   → `outputs/results/output_1d_###.json`. Verify immediately:
   ```bash
   python3 - <<'EOF'
   import json, glob
   d = json.load(open(sorted(glob.glob('outputs/results/output_1d_0*.json'))[-1]))
   print(d['total'], 'runs,', d['failures'], 'failures,',
         all(r['converged'] for r in d['runs']), 'all converged')
   EOF
   ```
   (`python3` is fine here: stdlib only.)
4. **Rename** the raw output so it survives future sweeps:
   `outputs/results/output_1d_N{X}.json` (e.g. `output_1d_N6.json`).
   Renaming creates a numbering gap — `nts-1d-run` auto-numbering picks the
   next free index, it does not reuse names.
5. **Extract + plot** — before overwriting, back up the previous order's
   data the same way:
   ```bash
   cp outputs/results/datos.json outputs/results/datos_N{prev}.json
   cp outputs/results/plots/scs_flux.png outputs/results/plots/scs_flux_N{prev}.png
   uv run nts-1d-data --latest --positions 0 100
   uv run nts-1d-plot
   ```
6. **Back up the new order** the same way after plotting, so each sweep ends
   with a complete set: `output_1d_N{X}.json`, `datos_N{X}.json`,
   `plots/scs_flux_N{X}.png`.

Report to the user: iterations range (first/last config), the pos-0 and
pos-100 flux trend vs kk, and the artifact paths.

## Multiplicative media / k_eff (1D)

The 1D solvers (`NTS_DD_1D`, `NTS_STEP_1D` and `NTS_SC_1D` over a shared
engine) solve the one-group S_N equations with isotropic fission:

```text
mu_m dPsi_m/dx + Sigma_t Psi_m
    = 1/2 [Sigma_s + nu*Sigma_f/k] Phi + 1/2 Q
```

`NU_SIGF` is **nu*Sigma_f** [cm^-1]. Do **not** multiply by `4*pi`: the
`sn-spectral` skill uses `4*pi*nu*Sigma_f` in its own convention, but the
solver equation already carries the `1/2`. The 2D C binaries do **not**
support fission.

### Modes

| `MODE` | `NU_SIGF` | `K_EFF` | Source | Purpose |
|---|---|---|---|---|
| `fixed_source` | 0 | — | `Q` / incoming | Historical, no fission |
| `eigenvalue` | > 0 | — | `Q = 0` | Compute `k_eff` |
| `fixed_k` | > 0 | > 0 | optional | Imposed-k / parametric |
| `driven` | > 0 | 1 (fixed) | required | Physical source + fission |

- **`eigenvalue`**: homogeneous problem. Requires `Q = 0` and zero incoming
  flux; vacuum and reflective boundaries are both valid. The amplitude is
  arbitrary; the solver normalizes it.
- **`driven`**: physical source problem. Fission is **not** divided by `k`.
  Requires `Q != 0` or incoming flux. A critical system with a source has no
  steady state; `driven` is for subcritical assemblies.
- **`fixed_k`**: imposes `k` in the denominator. With a source it is driven;
  without a source it is a mode-shape problem and `k_balance` is the critical
  `k` of the computed shape.
- If `MODE` is omitted: `NU_SIGF=0` -> `fixed_source`; `NU_SIGF>0` with no
  `K_EFF` -> `eigenvalue`; `NU_SIGF>0` with `K_EFF` -> `fixed_k`.
- Convergence: `max |1 - phi_new/phi_old| < epsilon` (`epsilon = 1e-5`;
  `eigenvalue` inner flux uses `max(epsilon, TOL_K)`, so with the defaults it
  stops at `1e-5`; pass `epsilon=1e-6` to reproduce the historical `k_eff`
  values). Cells with `phi_old = 0` fall back to an absolute difference.
- `iteration` counts completed flux updates (one per right + left sweep
  and scalar-flux update); `iteration_eigenvalue` counts power iterations
  and is `null` outside `eigenvalue`.

### Config keys

```python
"NU_SIGF": [0.11],   # nu*Sigma_f per zone [cm^-1]
"MODE": "eigenvalue",
"SPATIAL_SCHEME": "DD",  # DD (default) | STEP | SC
# "ZONE_NAMES": ["Reflector", "Core"],  # optional plot labels
# "K_EFF": 1.0,      # fixed_k only
"TOL_K": 1e-6,
"MAX_OUTER": 200,
"K0": 1.1,           # optional; default integral nu*Sf / integral Sa
# "POWER_KW": 10.0,  # optional power normalization
# "E_F_MEV": 200.0,
# "NU": 2.4,         # or "SIGMA_F": [0.045833]
# "AREA_CM2": 1.0,
```

### Spatial schemes

| `SPATIAL_SCHEME` | Order | Notes |
|---|---|---|
| `DD` | 2nd | Default; bit-for-bit backward compatible at equal tolerances |
| `STEP` | 1st | Implicit upwind (`psi_bar = psi_out`), positive, diffusive |
| `SC` | 2nd | Step characteristics; closest to DD on coarse meshes |

- The wizard and `nts-1d-config` ask
  `Spatial scheme (DD / STEP / SC) [DD]:` after the quadrature order.
- `nts-1d-run-dd`, `nts-1d-run-step` and `nts-1d-run-sc` force their scheme
  (same flags as `nts-1d-run`) and warn when the config says otherwise.
- Only the cell kernel changes: source, quadrature, boundaries and iteration
  are shared.
- S8/100 cells benchmark: DD `1.026661`, SC `1.026038`, STEP `1.017827`
  with the defaults; with `epsilon = TOL_K = 1e-6`: `1.026676`, `1.026054`,
  `1.017843` (the values pinned by the tests). STEP's ~0.9% gap is expected
  (first order), not a defect.
- No clipping or positivity constraints. DD can give negative angular fluxes
  in thick cells; report them, do not "fix" them.
### Solver modules

| Module | Responsibility |
|---|---|
| `NTS_DD_1D.py` | Diamond Difference scheme + compatibility facade (`Config`, `Runner`) |
| `NTS_STEP_1D.py` | Step (implicit upwind) scheme |
| `NTS_SC_1D.py` | Step Characteristic scheme (`theta` + `prepare()`) |
| `scheme.py` | `Method`, `Scheme` protocol, dispatch |
| `config.py` | Scheme-agnostic `Config` |
| `runner.py` | Shared transport engine (single-pass sweep) |

Per-method cards: `solvers/runners/NTS_DD_1D.md`, `NTS_STEP_1D.md`,
`NTS_SC_1D.md`. Full reference: `doc/SPATIAL_SCHEMES_EN.md`.

### Benchmark (20 cm, vacuum, S8)

`L=20 cm`, `Sigma_t=1.0`, `Sigma_s0=0.9`, `nu*Sigma_f=0.11`,
`NC=[100]`, `N=8`, vacuum:

| Order | `k_eff` (defaults) | `k_eff` (`epsilon = TOL_K = 1e-6`) |
|---|---|---|
| S2 | 1.02462 | 1.02464 |
| S4 | 1.02649 | 1.02651 |
| S8 | 1.02667 | 1.02668 |

`k_inf = 1.1` is the upper bound. Mesh convergence at S8 with
`epsilon = TOL_K = 1e-6`: 25 -> 1.026539, 50 -> 1.026649, 100 -> 1.026676,
200 -> 1.026683, 400 -> 1.026685 (defaults, `epsilon=1e-5`, give ~1.5e-5
less: 100 -> 1.026661, 200 -> 1.026667). Tighter tolerances converge to
~1.026689. The slab is slightly supercritical. The exact test is a reflective
slab: `k_eff = nu*Sigma_f / Sigma_a` (e.g. 0.3/0.5 = 0.6).

### Solver performance (1D)

- The engine is a **single-pass sweep**: `Runner.sweep()` computes the cell
  averages and the scalar/angular flux in the same traversal.
  `calculo_flujo()` is kept as a public, NumPy-vectorized API but is no longer
  used by the iteration.
- Sweep invariants (`dx`, `Σt`, `μ`, `|μ|`, `ω`, `θ`) are precomputed as Python
  floats; do not reintroduce attribute lookups or `abs()` in the inner loop.
- Inner scattering tolerance is `max(epsilon, TOL_K)`.
- Measured on this repo (Python 3.14, 20 cm, S8, I=200): eigenvalue ~0.8 s
  (618 sweeps) after the optimization, ~2.1 s before; fixed source ~0.13 s.
  The 5-zone S4 case is dominated by the dominance ratio (~11k sweeps).
- Details and before/after tables: `extras/mejoras_nts.md`.
- Pending (medium risk, not implemented): `extras/propuesta_dsa_cmfd.md`
  (convergence acceleration) and `extras/propuesta_barrido_vectorizado.md`
  (vectorized/compiled sweep).
- Comparison with the LabSN 1D JavaScript teaching solver (10 cases, balance,
  critique): `extras/analisis_codigo.md`.

### Multiplicative sweep

```python
# inputs_placeholder.py
"NU_SIGF": [nn],
"MODE": "eigenvalue",
"Q": [0],
"bound_left": [0]*4, "bound_right": [0]*4,
```

```bash
uv run nts-generate --place-holder nn 0.05 0.20 0.05
uv run nts-1d-run
uv run nts-1d-data --latest --positions 0 100
uv run nts-1d-plot --x NU_SIGF     # or --x k_eff
```

`datos.json` rows carry `NU_SIGF`, `k_eff`, `k_balance` and `mode`, so the
sweep can be summarised directly with `sweep_kpis.py`.

### Output and post-processing

Each run in `output_1d_###.json` adds `mode`, `k_eff`, `k_balance`,
`k_history`, `k_converged`, `outer_iterations`, `power_w`, `power_scale`.
`nts-1d-data` propagates `NU_SIGF`, `mode`, `k_eff`, `k_balance` to
`datos.json`. Use `nts-1d-plot --x k_eff` or `--x NU_SIGF` for the new
x-axes. `sweep_kpis.py` prints a `k_eff` table when the runs contain it.

### Validation

```bash
uv run python -m cli.run_tests -v
```

Covers: reflective infinite medium (exact), 20 cm benchmark, `fixed_k` at
`k*`, `driven` subcritical balance, 10 kW normalization, `NU_SIGF=0`
regression, invalid mode combinations.

## Manual and JSON configuration (1D)

For an agent-led questionnaire that ends in a validated JSON, see
[Guided setup of a new 1D problem](#guided-setup-of-a-new-1d-problem).

Besides `-c inputs.py`, the 1D runner accepts:

```bash
uv run nts-1d-run --manual
uv run nts-1d-run --json config.json
```

- **`--manual`**: step-by-step wizard. Asks geometry, materials, `N`, then
  fission (`NU_SIGF`, `MODE`, `K_EFF`), `TOL_K`/`MAX_OUTER`/`K0`, optional
  power normalization, `Q` (skipped for `eigenvalue`), and boundaries. It
  prints a summary and asks `Run? (y/n) [y]`; `n` cancels. Each run prints
  `Source: <file> | run <name>` under the `STARTING CALCULATION` banner.
- **`--json`**: a JSON object or a list of objects with the same keys as
  `inputs.py`. Names become `json_config_001`, etc.
- `--manual`, `--json` and `-c` are mutually exclusive; `-o` works in all
  three cases.
- Every output run embeds its effective `configuration`, so `nts-1d-data`
  and `sweep_kpis.py` work without a matching entry in `inputs.py`.
- Manual `eigenvalue` forces `Q=0` and zero incoming flux; `driven` requires
  `Q` or incoming flux; `fixed_k` without a source is a mode-shape
  calculation (read `k_balance`).

## Generating a 1D config with placeholders

```bash
uv run nts-1d-config -o outputs/inputs/config_1d_001.json
```

- Same prompts as `--manual`; without `-o`, writes
  `outputs/inputs/config_1d_###.json`.
- Numeric fields accept a number **or** a placeholder name (`kk`, `mm`,
  ...), including the spatial `NC` and `HR`. `NC` must expand to positive
  integers; `HR` to positive floats. `N`, `IZL` and `MAX_OUTER` must stay
  numeric.
- The JSON stores placeholders as strings, e.g. `"SCS": ["kk"]`.
- Expand and run:

```bash
uv run nts-generate --json outputs/inputs/config_1d_001.json \
  --place-holder kk 0.1 0.95 0.05 \
  --place-holder mm 0.05 0.20 0.05 \
  -o outputs/inputs/inputs_1d.json

uv run nts-1d-run --json outputs/inputs/inputs_1d.json
```

- `-o .json` writes a list; `-o .py` writes `config_dict_###`
  (`inputs.py`); without `-o`, `nts-generate` writes `inputs.py`.
- Placeholder ranges are combined in parallel by index (minimum length).
- Each expanded 1D config is validated with `Config(manual=False, **cfg)`;
  unresolved placeholders are rejected.
- Only the injected placeholder values are rounded; `TOL_K`/`K0` survive.

## Plotting 1D results

`nts-1d-plot` reads either a raw `output_1d_*.json` (`-r`) or the legacy
`datos.json` (`-i`):

```bash
# Raw output
uv run nts-1d-plot -r outputs/results/output_1d_016.json --list-runs
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind scalar --run manual
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind k-history --run manual

# Legacy datos.json
uv run nts-1d-plot -i outputs/results/datos.json --x k_eff
```

- More than one run in `-r` requires `--run NAME|INDEX`; `--list-runs`
  prints the options. `--run all` overlays runs for `scalar`/`k-history`;
  `angular` requires exactly one run.
- `angular_flux` is `(NTC, N)`: cell-averaged `ψ` per direction (columns by
  increasing `μ`), with `miu`/`omega` in the run. The scalar flux is the
  angular average `φ = 1/2 Σ ω ψ`.
- Power normalization: `P̃ = E_f · 1.602e-13 · A · 2 Σ Σf φ Δx`,
  `C_N = P_target/P̃`; `k_eff` does not change. `nts-1d-normalize`
  applies it to an existing JSON (`--power-kw` is required). If `NU` is
  missing, `NU = 2.49` (U-238 fast fission) is used; `--nu` overrides it.
- `nts-1d-run --excel [PATH]` also writes the workbook (Metadata, Runs,
  Zones, Regions, Boundaries, ScalarFlux, AngularFlux, Directions,
  k_history); without a path it uses the JSON stem. `nts-1d-excel`
  converts an existing output.
- `--kind k-history` only works for `MODE=eigenvalue`.
- Scalar and angular plots shade each region, draw dashed interfaces and
  label them `R1`, `R2`, ... with the zone name. Names come from the optional
  `ZONE_NAMES` config key or from `--zone-names "A,B,C"` (CLI wins); without
  them the labels are `Zone 1`, `Zone 2`, ...
- Default outputs: `outputs/results/plots/scalar_flux.png`,
  `angular_flux.png`, `k_history.png`.

## Adding a quadrature order (cuadraturas.py)

`solvers/runners/cuadraturas.py` is a flat `DATA` dict with columns
`N`, `m`, `mu_m`, `omega_m`. Conventions that make edits safe (the existing
N=2/4/8 rows all follow them):

- Only the **positive-μ half** is stored, with `m = 1` as the **largest** μ
  (descending μ as m grows).
- `omega_m` entries are the **per-node Gauss-Legendre weights** — the
  positive-half weights must **sum to exactly 1.0** (`∫₀¹ dμ = 1`). Doubling
  weights "to account for ±μ" is wrong: N=4 stores 0.34785, not 0.69570.
- After editing, verify all orders still sum to 1:
  ```bash
  uv run python -c "
  import sys; sys.path.insert(0,'solvers/runners')
  from cuadraturas import DATA
  import pandas as pd
  df = pd.DataFrame(DATA)
  for n in sorted(set(df.N)):
      s = df[df.N==n]
      print(n, s.omega_m.sum())
  "
  ```
- **The silent trap**: a config with an N that has no row does not error —
  the 1D solver prints `Warning: no data for S{N}, falling back to S2.` and
  runs S2 anyway, while `Config.N` still reports the requested order. When a
  user asks for an order not in the table, either add the rows first or
  surface the warning loudly instead of reporting S2 results as S{N}.
- Boundary vectors in the config must have length N/2:
  `bound_left=[1]*int(N/2)`, `bound_right=[0]*int(N/2)` for the standard
  isotropic-in / vacuum-out problem (`reflex_*` = False).
- Tabulated today: N=2, 4, 6, 8 (Gauss-Legendre). Anything else needs rows
  added before it will run at the right order.

## Validation gates and coordinates

- Zone physics: the **2D Pydantic config** enforces `σs < σt`; the 1D
  `Config` does **not** validate it (only `HR > 0`, `IZL` in range, `N` even).
  Check `σs ≤ σt` by hand for 1D configs: `σs > σt` gives negative absorption
  and unphysical amplification.
- 2D gates: `N` even; `ZMAP` values in `[1, NZ]`; `TOL ∈ [1e-7, 1e-2]`
  (1D defaults: ε=1e-5 relative, `max_iter=2000`).
- 1D multiplicative: `NU_SIGF >= 0`; `K_EFF > 0` for `fixed_k`;
  `eigenvalue` requires `Q=0` and zero incoming flux; `driven` requires
  `Q != 0` or incoming flux and forces `k=1`; `POWER_KW` requires
  `SIGMA_F` or `NU`.
- `BC` order is **[left, right, bottom, top]** (0.0 vacuum, 1.0 reflective).
  Some older docs claim another order — the code and `core/input_builder.py`
  are the truth.
- Positions in `scalar_flux` are **cell centres**: `dx = HR/NC` summed per
  cell index, so pos `i` ≈ (i+0.5)·dx. For HR=20, NC=101: pos 0 = 0.099 cm,
  pos 100 = 19.901 cm (vacuum face).
- Pydantic ignores JSON keys starting with `_` — that is how
  `templates/base_input.json` carries inline comments.

## KPI extraction and summaries

For comparative summaries across orders, use the bundled script instead of
reinventing the join (it reads any number of `output_1d_*.json`, aligns runs
by SCS, and prints markdown tables directly usable in meeting reports):

```bash
uv run python skills/nts-pinns-autopilot/scripts/sweep_kpis.py \
    outputs/results/output_1d_N4.json outputs/results/output_1d_N6.json \
    outputs/results/output_1d_N8.json
```

KPI conventions established in this project (see
`extras/reunion_14_9/Resume.md`):

- Iterations min (kk=0.10) / max (kk=0.95) per order — source-iteration cost.
- `flux_0` (source surface) and `flux_100` (vacuum surface) per kk.
- Convergence-vs-order KPI: `max |flux₀(S_N) − flux₀(S8)|` treating S8 as
  reference. S4 overshoots pos-0 flux; higher orders lower it.
- Diffusion limit: for kk ≥ 0.55 orders agree within ~1e-3.

Dataset sizing: each run yields `NC` scalar-flux cells (+1 angular-flux node
vector); total samples = Σ orders × configs × NC.

## Common traps

- `datos.json` and `plots/scs_flux.png` are **overwritten** by every
  extract/plot run — always snapshot per-order variants before re-running.
- `nts-1d-data --latest` picks the alphabetically-last `output_1d_*.json`,
  so renamed files like `output_1d_N6.json` sort *after* the numeric ones —
  fine, but never name the raw output with something that sorts before the
  file you intended.
- `execution/parallel.py` helpers (`run_batch`, `run_solver_comparison`)
  write `output_*.json`; anything writing `.txt` is a stale path.
- 2D solver outputs are JSON written directly by the binaries
  (`STATUS` 0 = success); `STATUS != 0` → check the 11-line input format in
  `doc/NTS_DOCUMENTATION.md`.
- Iterations blow up as kk → 1 (c = σs/σt ≈ 1): 9 iterations at c=0.1, ~215
  at c=0.95 with ε=1e-5. That is expected source-iteration behavior, not a
  bug; accelerating or loosening ε is the remedy, not a bugfix.
- `MODE='eigenvalue'` with `Q != 0` is rejected on purpose: that is a driven
  problem, not an eigenvalue. Use `MODE='driven'` (k=1) or `fixed_k`.
- `fixed_k` with no source is a **mode-shape** calculation: the amplitude is
  arbitrary, and only `k = k*` gives a stationary solution. Read
  `k_balance`, not the raw amplitude.
- At `k = k*` with a source the operator is singular; there is no steady
  state. Do not combine `K_EFF = k*` with `Q != 0`.
- Normalize the **whole** state (`scalar_flux`, `PSI_RIGHT`, `PSI_LEFT`,
  `angular_flux`) when renormalizing; scaling only the scalar flux makes the
  next sweep inconsistent.
- `4*pi` trap: `NU_SIGF` is plain `nu*Sigma_f`. The spectral skill's `4*pi`
  convention does not apply here.
- `POWER_KW` needs a way to get `Sigma_f`: provide `SIGMA_F` per zone or
  `NU` (nu_bar). The normalization scales the flux but does not change
  `k_eff`.
- `--manual` does not run until you confirm `Run? (y/n) [y]` (Enter or `y`
  runs); answering `n` cancels with rc 0 and writes no JSON.
- `--json` must be an object or a list of objects; a scalar or a list of
  scalars is rejected. `--manual`, `--json` and `-c` are mutually exclusive.
- Manual/JSON runs embed `configuration`, but older outputs do not. If
  `nts-1d-data` says a config is missing, pass the matching `--inputs`.
- `nts-1d-plot -r` with several runs requires `--run`; use `--list-runs`
  first. `--run all` is only for `scalar`/`k-history`.
- `angular_flux` is the directional field `(NTC, N)`, not the weighted sum.
  `scalar_flux` is the angular average `φ = 1/2 Σ ω ψ`; reaction rates use
  `2 φ` (balance and power already include that factor).
- `--kind k-history` only produces a plot for `MODE=eigenvalue`; a
  `fixed_k`/`driven`/`fixed_source` run has an empty `k_history`.
- `-r` and `-i` are mutually exclusive; `-i` is the legacy `datos.json`
  mode.
- `nts-1d-config` accepts placeholders in `NC`/`HR` too; `NC` must expand
  to positive integers. `N`, `IZL` and `MAX_OUTER` must be numeric.
- A config with placeholders is not runnable: expand it with
  `nts-generate --json ... -o ...` first. `nts-1d-run` will fail with
  “could not convert string to float” otherwise.
- `nts-generate --json` rounds only the injected placeholder values; it
  does not round `TOL_K`, `K0` or other config floats.
