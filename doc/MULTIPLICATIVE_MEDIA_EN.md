# Multiplicative media and effective multiplication factor (`k_eff`)

Guide to the multiplicative mode of the 1D solver `NTS_DD_1D`
(`solvers/runners/NTS_DD_1D.py`).

> **Scope:** this feature is exclusive to the Python 1D solver. The 2D C
> solvers (`NTS_DD`, `NTS_LD`, `NTS_STEP`, `NTS_RM_CN`, `NTS_RM_LLN`) remain
> fixed-source and do not accept `NU_SIGF` or `k_eff`.
>
> Spanish version: [MULTIPLICATIVE_MEDIA.md](MULTIPLICATIVE_MEDIA.md).

## 1. Equation solved

For one energy group, isotropic scattering and isotropic fission:

$$
\mu_m \frac{d\Psi_m(x)}{dx} + \Sigma_t(x)\Psi_m(x)
= \frac12\left[\Sigma_s(x) + \frac{\nu\Sigma_f(x)}{k}\right]\Phi(x)
+ \frac12 Q(x),
\qquad m = 1,\dots,N
$$

with

$$
\Phi(x) = \sum_{m>0} w_m \left[\Psi_m^+(x) + \Psi_m^-(x)\right].
$$

Code conventions:

- `NU_SIGF` is **νΣf** (cm⁻¹), not `4π·νΣf`. The `1/2` of the isotropic
  source is already in the equation and in the sweep.
- `SIGMA_F` is **Σf** (cm⁻¹). It is optional and only used for power
  normalization.
- If `NU_SIGF` is given but `SIGMA_F` is not, power normalization uses
  `Σf = νΣf / NU`, where `NU` is the number of neutrons per fission.
- `Q` is the external source per region and `bound_left`/`bound_right` are
  the incoming fluxes at the boundaries.

## 2. The four modes

| `MODE` | `NU_SIGF` | `K_EFF` | Source | What it solves |
|---|---|---|---|---|
| `fixed_source` | 0 | — | `Q` or incoming flux | Transport without fission (historical behaviour) |
| `eigenvalue` | > 0 | — | `Q = 0`, homogeneous boundaries | Computes `k_eff` and the fundamental shape |
| `fixed_k` | > 0 | > 0 | optional | Fission scaled by an imposed `k` |
| `driven` | > 0 | 1 (fixed) | required | Physical source + fission problem |

### 2.1 `fixed_source`

This is the original mode. `NU_SIGF = 0`; the source is `Q` and/or the
incoming flux. It does not compute `k_eff`.

### 2.2 `eigenvalue`

Solves the **homogeneous** problem:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \frac{\nu\Sigma_f}{k}\right]\Phi,
\qquad Q = 0,
$$

and finds the largest `k` for which a non-trivial solution exists. That is
the effective multiplication factor. The flux amplitude is arbitrary; the
solver normalizes it (maximum = 1) and, if requested, rescales it to a
power.

**Condition:** `Q = 0` and zero incoming flux. Boundaries may be vacuum or
reflective, because both are homogeneous. With an external source the
problem is no longer an eigenvalue; use `fixed_k` or `driven`.

### 2.3 `fixed_k`

Solves the equation with an imposed `k`:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \frac{\nu\Sigma_f}{k_{\text{imposed}}}\right]\Phi
+ \frac12 Q.
$$

- **With a source** (`Q ≠ 0` or incoming flux): linear problem with a unique
  solution for `k ≠ k*`; the amplitude is set by the source.
- **Without a source:** homogeneous problem. Only at `k = k*` is there a
  non-trivial stationary solution. If `k ≠ k*`, the stationary solution is
  zero; the solver normalizes and reports `k_balance = P/(A+L)`, the critical
  `k` estimated from the obtained shape.

`fixed_k` is useful for parametric studies and to verify the eigenvalue: run
it at `k = k*`; the shape should remain stationary and `k_balance ≈ k*`.

### 2.4 `driven`

This is the physical source problem. It imposes `k = 1` (fission is not
divided by `k`) and requires `Q ≠ 0` or incoming flux:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \nu\Sigma_f\right]\Phi + \frac12 Q.
$$

If the system is subcritical (`k_eff < 1`), the solution is finite and
unique. If it is supercritical (`k_eff > 1`), the flux grows without bound
and the iteration does not converge. The system `k_eff` is computed
separately with `eigenvalue`; `driven` reports `k_balance` as a diagnostic.

> **Do not mix `k = k*` with a source.** At `k = k*` the operator is
> singular: a source in a critical system has no steady state (the flux
> grows). The code rejects `MODE='driven'` with `K_EFF ≠ 1` and
> `MODE='eigenvalue'` with a source.

## 3. Configuration

New fields in the `outputs/inputs/inputs.py` dictionaries:

| Field | Type | Default | Description |
|---|---|---|---|
| `NU_SIGF` | list per zone | `[0.0]*NZ` | νΣf in cm⁻¹ |
| `SIGMA_F` | list per zone | `None` | Σf in cm⁻¹ (for power) |
| `MODE` | str | inferred | `fixed_source`, `eigenvalue`, `fixed_k`, `driven` |
| `K_EFF` | float | `None` | imposed `k`; `fixed_k` only |
| `TOL_K` | float | `1e-6` | `k_eff` convergence tolerance |
| `MAX_OUTER` | int | `200` | outer power-iteration count |
| `K0` | float | `None` | initial guess; `None` → `∫νΣf/∫Σa` |
| `POWER_KW` | float | `None` | enables power normalization |
| `E_F_MEV` | float | `200.0` | recoverable energy per fission |
| `NU` | float | `None` | neutrons per fission (if no `SIGMA_F`) |
| `AREA_CM2` | float | `1.0` | cross-sectional area of the slab |

If `MODE` is omitted, the solver infers:

- all `NU_SIGF` zero → `fixed_source`;
- `NU_SIGF > 0` and `K_EFF = None` → `eigenvalue`;
- `NU_SIGF > 0` and `K_EFF` given → `fixed_k`.

Declare `MODE` explicitly to avoid ambiguity.

### Example: 20 cm benchmark

Homogeneous 20 cm slab, vacuum on both sides, σt = 1.0 cm⁻¹,
σs0 = 0.9 cm⁻¹, νσf = 0.11 cm⁻¹:

```python
config_dict = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [100],
    "HR": [20.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.9],
    "NU_SIGF": [0.11],
    "Q": [0.0],
    "N": 8,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0, 0, 0, 0],
    "bound_right": [0, 0, 0, 0],
    "MODE": "eigenvalue",
    "TOL_K": 1e-6,
    "MAX_OUTER": 200,
}
```

Run:

```bash
uv run nts-1d-run
```

Expected output (S8, 100 cells):

```text
EIGENVALUE CONVERGED: k_eff = 1.026676...
k_balance (P/(A+L)) = 1.026677...
```

### 3.1 Interactive manual configuration

```bash
uv run nts-1d-run --manual
# equivalent
uv run nts run-1d --manual
```

The wizard asks, step by step:

1. geometry (`NC`, `HR`, `IZL`) and materials (`SCT`, `SCS`);
2. quadrature `N` (2, 4, 6, 8; default 8);
3. if fission is enabled: `NU_SIGF` per zone, `MODE`, `K_EFF` (`fixed_k`
   only), `TOL_K`, `MAX_OUTER`, `K0`;
4. optional power normalization (`POWER_KW`, `E_F_MEV`, `AREA_CM2`, and
   conversion with `NU` or `SIGMA_F`);
5. `Q` per region (skipped for `eigenvalue`, where it is 0);
6. reflective/vacuum boundaries and incoming flux per direction (forced to
   0 for `eigenvalue`);
7. configuration summary and confirmation.

Wizard validations:

- `NU_SIGF ≥ 0`;
- `fixed_k` requires `K_EFF > 0`;
- `driven` requires `Q ≠ 0` or incoming flux;
- `POWER_KW` requires `NU` or `SIGMA_F`;
- `IZL` in `[1, num_zones]`;
- `NC`/`IZL` integers; `HR > 0`;
- `N` even and tabulated (otherwise the S2 fallback warning is shown).

### 3.2 Loading from JSON

```bash
uv run nts-1d-run --json config_multiplicative.json
```

The file may be one object or a list of objects with the same keys as an
`inputs.py` dict. Example for the benchmark:

```json
{
  "num_regions": 1,
  "num_zones": 1,
  "NC": [100],
  "HR": [20.0],
  "IZL": [1],
  "SCT": [1.0],
  "SCS": [0.9],
  "NU_SIGF": [0.11],
  "Q": [0.0],
  "N": 8,
  "reflex_izq": false,
  "reflex_der": false,
  "bound_left": [0, 0, 0, 0],
  "bound_right": [0, 0, 0, 0],
  "MODE": "eigenvalue"
}
```

`--manual`, `--json` and `-c` are mutually exclusive. Each run stores its
effective `configuration` in the output JSON; `nts-1d-data` and
`sweep_kpis.py` use it, so the `config_name` does not need to exist in
`outputs/inputs/inputs.py`.

### 3.3 Configuration generator with placeholders

```bash
uv run nts-1d-config -o outputs/inputs/config_1d_001.json
```

This is the same wizard as `--manual`, but it writes JSON instead of
running. In numeric fields you may type a number or a placeholder:

```text
Sigma_Scattering Zone 1 (number or placeholder, e.g. kk): kk
nu*Sigma_f Zone 1 [cm^-1] (number or placeholder, e.g. mm): mm
```

The resulting JSON contains:

```json
{
  "SCS": ["kk"],
  "NU_SIGF": ["mm"],
  "MODE": "eigenvalue",
  "TOL_K": 1e-6
}
```

Expand and run:

```bash
uv run nts-generate --json outputs/inputs/config_1d_001.json \
  --place-holder kk 0.1 0.95 0.05 \
  --place-holder mm 0.05 0.20 0.05 \
  -o outputs/inputs/inputs_1d.json

uv run nts-1d-run --json outputs/inputs/inputs_1d.json
```

- `-o .json` writes a list of configs; `-o .py` writes `config_dict_###`
  (`inputs.py`).
- Without `--json`, `nts-generate` still reads
  `outputs/inputs/inputs_placeholder.py`.
- Placeholders are combined in parallel by index (minimum length).
- Only injected values are rounded; `TOL_K`, `K0`, etc. are preserved.
- `NC` and `HR` accept placeholders. `NC` must expand to positive integers;
  `HR` to positive floats. `N`, `IZL` and `MAX_OUTER` do not accept
  placeholders.

## 4. Algorithm

### 4.1 Power iteration (`eigenvalue`)

1. `k ← k0` (`k0 = ∫νΣf dx / ∫(Σt−Σs) dx` if not given).
2. `Φ ← 1` (flat positive guess).
3. Repeat for `outer = 1..MAX_OUTER`:
   1. Freeze the fission source: `S_f = ½ νΣf Φ / k`.
   2. Inner scattering iteration until the relative change of `Φ` is below
      `min(epsilon, TOL_K)`.
   3. `P_new = ∫νΣf Φ_new dx`.
   4. `k_new = k · P_new / P_old`.
   5. Normalize the **entire** state (`Φ`, `Ψ⁺`, `Ψ⁻`, `angular_flux`).
   6. `P_old ← ∫νΣf Φ dx`.
   7. Stop if `|k_new − k| / |k_new| < TOL_K`.
4. Report `k_eff`, `k_balance` and the history.

The inner tolerance is tied to `TOL_K` so scattering error does not bias
`k_eff`.

### 4.2 `fixed_k`

1. `k ← K_EFF`.
2. Each sweep: `S_f = ½ νΣf Φ / k`.
3. Without a source, normalize the state on each iteration and warn that the
   amplitude is arbitrary.
4. Converge on flux; report `k_balance`.

### 4.3 `driven`

Same as `fixed_k` with `k = 1`, but requires an external source. It does not
normalize: the source sets the amplitude.

### 4.4 Global balance

With the converged flux:

$$
P = \int \nu\Sigma_f \Phi\,dx,\qquad
A = \int (\Sigma_t-\Sigma_s)\Phi\,dx,\qquad
L = \text{net leakage},
$$

$$
k_{\text{balance}} = \frac{P}{A+L}.
$$

Net leakage is **outgoing − incoming** at each boundary. With reflective
boundaries, `L = 0`; with vacuum, `L` is the outgoing leakage. For the
eigenvalue, `k_eff ≈ k_balance` must hold.

## 5. Power normalization

`k_eff` does not depend on the flux scale. To fix the amplitude:

$$
P = A\,E_f\,(1.602176634\times10^{-13})
\int_0^L \Sigma_f \Phi\,dx,
$$

with `P` in W, `A` in cm², `E_f` in MeV/fission and `Σf` in cm⁻¹. If
`SIGMA_F` is not given, `Σf = νΣf / NU`.

Example: `POWER_KW = 10`, `E_F_MEV = 200`, `NU = 2.4`, `AREA_CM2 = 1`.
The solver scales `Φ`, `Ψ⁺`, `Ψ⁻` and `angular_flux` by the same factor and
reports `power_w` and `power_scale`.

> `E_f = 200 MeV`, `ν = 2.4` and `A = 1 cm²` are working choices. If the
> course uses other values, change them in the configuration.

## 6. Reference benchmark

Data: `L = 20 cm`, `σt = 1.0`, `σs0 = 0.9`, `νσf = 0.11`, vacuum.

| Order | `k_eff` (100 cells, `TOL_K=1e-6`) |
|---|---|
| S2 | 1.024641 |
| S4 | 1.026509 |
| S8 | 1.026676 |

Mesh convergence (S8):

| Cells | `k_eff` |
|---|---|
| 25 | 1.026539 |
| 50 | 1.026649 |
| 100 | 1.026676 |
| 200 | 1.026683 |
| 400 | 1.026685 |

With finer `epsilon`/`TOL_K`, values converge to ~`1.026689`.

Cross-checks:

- `k_inf = νΣf / (Σt − Σs) = 1.1` (upper bound).
- Analytical S2: `1.024654` (matches the numerical result at the `1e-5`
  level).
- P1 diffusion: `1.026409` (same order).
- The system is slightly supercritical (`k_eff > 1`); valid for an
  eigenvalue.

### Exact test: infinite reflective medium

With reflective boundaries on both sides there is no leakage and the
fundamental flux is flat:

$$
k_{eff} = \frac{\nu\Sigma_f}{\Sigma_t-\Sigma_s}.
$$

This case is used as an acceptance test (`tests/test_dd_1d_fission.py`).

## 7. Output

Each run in `output_1d_###.json` adds:

```json
{
  "mode": "eigenvalue",
  "k_eff": 1.0266764379,
  "k_balance": 1.0266775219,
  "k_history": [1.1, 1.08, ...],
  "k_converged": true,
  "outer_iterations": 25,
  "power_w": null,
  "power_scale": 1.0
}
```

`nts-1d-data` adds `NU_SIGF`, `mode`, `k_eff` and `k_balance` to each
`datos.json` row. `nts-1d-plot --x k_eff` plots flux against `k_eff`;
`--x NU_SIGF` plots against νΣf.

### 7.1 Plots from `output_1d`

`nts-1d-plot` reads the raw JSON (`runs[]`), not only `datos.json`:

```bash
# List available runs
uv run nts-1d-plot -r outputs/results/output_1d_016.json --list-runs

# Φ(x)
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind scalar --run manual

# Angular flux: one line per direction, same axes, colors and legend
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual --directions 0 1

# k_eff vs outer iteration
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind k-history --run manual

# Legacy mode (datos.json)
uv run nts-1d-plot -i outputs/results/datos.json --x k_eff
```

Rules:

- If the file has more than one run, `--run NAME|INDEX` is required;
  `--list-runs` shows the options. `--run all` overlays all runs for
  `scalar`/`k-history`; `angular` requires exactly one.
- `angular_flux` is stored as `ω_m(ψ⁺ + ψ⁻)`; the Y-axis label says so.
- `--kind k-history` only works with `MODE=eigenvalue`; other modes have an
  empty history.
- Default outputs: `outputs/results/plots/scalar_flux.png`,
  `angular_flux.png`, `k_history.png`.

## 8. Validation

```bash
uv run nts-test -v
```

Included tests:

- infinite reflective medium: `k = νΣf/Σa`;
- 20 cm benchmark;
- `fixed_k` at `k*` against the eigenvalue;
- subcritical `driven`: `k_balance = 0.5`;
- 10 kW power normalization;
- `NU_SIGF = 0` regression;
- mixed boundaries (reflective/vacuum) with no artificial flux injection;
- `MODE` inference when omitted;
- invalid mode combinations;
- spatial placeholders (`NC`/`HR`) and rejection of non-integer `NC`.

## 9. Known pitfalls

1. **`4π`:** the `sn-spectral` skill uses
   `c = Σs/Σt + 4πν̄Σf/(kΣt)` in its convention. Here **no** `4π` is used;
   the equation already has `1/2`.
2. **`eigenvalue` with a source:** not an eigenvalue. Use `driven` or
   `fixed_k`.
3. **`k = k*` with a source:** singular operator, no steady state.
4. **`fixed_k` without a source:** arbitrary amplitude; only a mode shape
   and `k_balance` are obtained.
5. **Normalizing only the scalar flux:** breaks consistency with the angular
   fluxes. The solver scales the whole state.
6. **DD with optically thick cells:** may produce negative fluxes; refine
   the mesh.
7. **Slow power iteration:** if the dominance ratio is close to 1, increase
   `MAX_OUTER` or refine; it is not a bug.
8. **`NU_SIGF` vs `SIGMA_F` vs `NU`:** `NU_SIGF` is νΣf; `SIGMA_F` is Σf;
   `NU` is only used to convert one into the other for power normalization.
9. **N=6 weight:** fixed to `0.4679139345726910` in `cuadraturas.py`.
10. **Placeholders:** `NC` must expand to positive integers; `N`, `IZL` and
    `MAX_OUTER` must remain numeric.

## 10. Relation to `sn-spectral`

The `sn-spectral` skill computes the spectrum of an infinite homogeneous
medium: eigenvalues `ν`, eigenfunctions and the constant

$$
c = \frac{\Sigma_s}{\Sigma_t} + \frac{4\pi\,\nu\Sigma_f}{k\Sigma_t}.
$$

At criticality in an infinite medium, `c = 1`; in that skill's convention
this gives `k = 4πνΣf/(Σt−Σs)`. `NTS_DD_1D` uses the standard convention
without `4π`, so the `k_eff` of a finite slab is **not** obtained directly
from `sn-spectral`: the boundary-value problem with vacuum or reflective
boundaries must be solved.

## 11. Internal references

- `README.md` — CLI and configuration format reference.
- `doc/QUICKSTART.md` — cheatsheet.
- `doc/NTS_DOCUMENTATION.md` — 2D C solver documentation.
- `tests/test_dd_1d_fission.py` — acceptance tests.
- `skills/nts-pinns-autopilot/SKILL.md` — operational skill guide.
- `doc/MULTIPLICATIVE_MEDIA.md` — Spanish version.
