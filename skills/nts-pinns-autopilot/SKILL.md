---
name: nts-pinns-autopilot
description: >-
  Operates the NTS Automation System (neutron-transport-PINNs, v2.1.0), a CLI for
  SN neutron transport simulations: generating/validating inputs, running the 2D
  C solvers (NTS_DD/LD/STEP/RM_CN/RM_LLN) and the Python 1D Diamond-Difference
  solver, launching parametric sweeps (placeholders to configs to runs to
  datos.json to plots), adding SN quadrature orders (N=2,4,6,8), extracting
  flux KPI tables, and solving 1D multiplicative media with fission and k_eff
  (MODE=eigenvalue|fixed_k|driven, NU_SIGF, power iteration, power
  normalization). Use this skill ANY time the user works in this repository,
  runs `uv run nts*` commands, or mentions kk/SCT/SCS/NU_SIGF placeholders,
  k_eff, medio multiplicativo, eigenvalue, fixed_k, driven, inputs_placeholder.py,
  inputs.py, cuadraturas.py, output_1d_*.json, datos.json, N=4/N=6/N=8
  quadrature orders, or asks to run/compare/plot DD simulations or prepare KPI
  summaries — even if they never name the system.
---

# NTS PINNs Autopilot

Operational knowledge for the NTS Automation System in this repository.
Full reference docs live in `README.md`, `doc/QUICKSTART.md` and
`doc/NTS_DOCUMENTATION.md` — read them when you need background theory or
solver method selection. This file is the short, operational path.

## Environment rules

- Every command runs through `uv`: `uv run nts …`, `uv run python …`.
  The venv is Python 3.14 and only `uv run python` has the project deps
  (pandas, matplotlib, pydantic). Bare `python3` will fail on imports.
- `outputs/` is gitignored: never commit anything inside it, and treat files
  there as regenerable except the curated `*_N*.json` datasets the sweep flow
  keeps (renamed by hand).
- The 2D solvers are compiled binaries in `solvers/runners/` (checked with
  `uv run nts status`, which lists all five: NTS_DD, NTS_LD, NTS_STEP,
  NTS_RM_CN, NTS_RM_LLN).

## Command map

Main CLI (`cli/commands.py` via `main.py`):

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `nts status` | Solver binaries + file counts | — |
| `nts validate <config.json>` | Pydantic validation + summary | — |
| `nts generate <config.json>` | JSON config → `input_###.txt` | `-p` preview, `--place-holder NAME START END STEP` (repeatable, nargs=4) |
| `nts run` | 2D binaries (parallel) | `-s SOLVER`, `-i input.txt…`, `-p N` (default 4) |
| `nts run-1d` | Python 1D solver over `inputs.py` | `-c` config path, `-o` output path |
| `nts list inputs\|outputs` | Rich tables of generated files | — |
| `nts show <result.json>` | STATUS / ITER / CPU summary | — |
| `nts plot [-r result.json]` | MFLUX heatmap of a 2D JSON result | `-o` png path, `--show` |

Shortcuts (`pyproject.toml` scripts):

| Shortcut | Equivalent |
|----------|-----------|
| `nts-generate` | `nts generate` in placeholder mode |
| `nts-1d-run` | `nts run-1d` |
| `nts-1d-data [--latest] [--positions 0 50 100]` | extract fluxes → `datos.json` |
| `nts-1d-plot [-i datos.json] [-o plot.png] [--x SCS\|NU_SIGF\|k_eff]` | flux vs the chosen x variable, one subplot per position |

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

`NTS_DD_1D` solves the one-group S_N equations with isotropic fission:

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

### Config keys

```python
"NU_SIGF": [0.11],   # nu*Sigma_f per zone [cm^-1]
"MODE": "eigenvalue",
# "K_EFF": 1.0,      # fixed_k only
"TOL_K": 1e-6,
"MAX_OUTER": 200,
"K0": 1.1,           # optional; default integral nu*Sf / integral Sa
# "POWER_KW": 10.0,  # optional power normalization
# "E_F_MEV": 200.0,
# "NU": 2.4,         # or "SIGMA_F": [0.045833]
# "AREA_CM2": 1.0,
```

### Benchmark (20 cm, vacuum, S8)

`L=20 cm`, `Sigma_t=1.0`, `Sigma_s0=0.9`, `nu*Sigma_f=0.11`,
`NC=[100]`, `N=8`, vacuum:

| Order | `k_eff` |
|---|---|
| S2 | 1.02464 |
| S4 | 1.02651 |
| S8 | 1.02668 |

`k_inf = 1.1` is the upper bound. Mesh convergence at S8 (default
`TOL_K=1e-6`): 25 -> 1.026539, 50 -> 1.026649, 100 -> 1.026676,
200 -> 1.026683, 400 -> 1.026685. Tighter tolerances converge to ~1.026689. The slab is slightly supercritical. The exact test is a
reflective slab: `k_eff = nu*Sigma_f / Sigma_a` (e.g. 0.3/0.5 = 0.6).

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
uv run python -m unittest discover -s tests -v
```

Covers: reflective infinite medium (exact), 20 cm benchmark, `fixed_k` at
`k*`, `driven` subcritical balance, 10 kW normalization, `NU_SIGF=0`
regression, invalid mode combinations.

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
  the 1D solver prints `Advertencia: No hay datos para S{N}, usando S2.` and
  runs S2 anyway. When a user asks for an order not in the table, either add
  the rows first or surface the warning loudly instead of reporting S2
  results as S{N}.
- Boundary vectors in the config must have length N/2:
  `bound_left=[1]*int(N/2)`, `bound_right=[0]*int(N/2)` for the standard
  isotropic-in / vacuum-out problem (`reflex_*` = False).
- Tabulated today: N=2, 4, 6, 8 (Gauss-Legendre). Anything else needs rows
  added before it will run at the right order.

## Validation gates and coordinates

- Zone physics: `σs < σt` per zone; `N` even; `ZMAP` values in `[1, NZ]`;
  `TOL ∈ [1e-7, 1e-2]` (defaults: ε=1e-5 relative, max_iter=2000 in the 1D
  solver).
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
