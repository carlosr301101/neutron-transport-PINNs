# Spatial discretization schemes (DD, STEP, SC)

Reference for the cell schemes of the Python 1D solver
(`solvers/runners/NTS_DD_1D.py`).

> **Scope:** exclusive to the 1D solver. The 2D C programs (`NTS_DD`,
> `NTS_LD`, `NTS_STEP`, `NTS_RM_CN`, `NTS_RM_LLN`) keep their own scheme and
> are not affected by `SPATIAL_SCHEME`.
>
> Spanish version: [SPATIAL_SCHEMES.md](SPATIAL_SCHEMES.md).

## 1. What the schemes share

The selection changes **only the cell kernel**. Everything else is common:

- total isotropic source `S = ½(Q + ΣsΦ) + S_fission` (`S_fission` already
  carries its `½`);
- angular quadrature (`N`, `miu_m`, `omega_m`);
- vacuum and reflective boundary conditions;
- source iteration, power iteration and convergence criteria;
- `k_eff` estimation and optional power normalization.

The sweep keeps the same two loops (cells left→right for `μ>0`, right→left
for `μ<0`) and the same interface storage (`PSI_RIGHT`, `PSI_LEFT`).

## 2. Cell balance

Every scheme satisfies, per cell and per ordinate,

$$
\frac{|\mu|}{\Delta x}\left(\psi_{\text{out}}-\psi_{\text{in}}\right)
+ \Sigma_t \bar{\psi} = S .
$$

The schemes differ in how they close this relation: each one picks a
different approximation for `ψ̄` and derives `ψ_out` from it.

Notation: `a = |μ|/Δx`, `α = ΣtΔx/|μ|`.

## 3. Diamond Difference (`DD`, default)

$$
\psi_{\text{out}} = \frac{(a-\Sigma_t/2)\psi_{\text{in}}+S}{a+\Sigma_t/2},
\qquad
\bar{\psi} = \frac{\psi_{\text{in}}+\psi_{\text{out}}}{2}.
$$

Second order in `Δx`. It is the historical scheme, so `"DD"` reproduces the
previous results exactly (same floating-point operations).

## 4. Step Difference (`STEP`)

$$
\psi_{\text{out}} = \frac{a\,\psi_{\text{in}}+S}{a+\Sigma_t},
\qquad
\bar{\psi} = \psi_{\text{out}}.
$$

Implicit upwind: the cell average is taken as the **downstream** face value.
This makes the scheme unconditionally positive (no negative fluxes), at the
price of first-order accuracy.

> The explicit variant (`ψ̄ = ψ_in`) is **not** implemented: it is unstable
> for optically thick cells.

## 5. Step Characteristics (`SC`)

$$
\theta = \coth\!\left(\frac{\alpha}{2}\right)-\frac{2}{\alpha},
\qquad
\bar{\psi} = \frac{1+\theta}{2}\psi_{\text{out}}
+ \frac{1-\theta}{2}\psi_{\text{in}},
$$

$$
\psi_{\text{out}} =
\frac{\left[a-\frac{\Sigma_t}{2}(1-\theta)\right]\psi_{\text{in}}+S}
{a+\frac{\Sigma_t}{2}(1+\theta)} .
$$

`θ` is a convex weight in `[0,1)`: it tends to `0` for thin cells (SC → DD)
and to `1` for thick cells (the average → the STEP convention). Second order
in `Δx`.

### Numerics of `θ`

- `α = 0` (no attenuation) returns `θ = 0`.
- `α < 1e-3` uses the series
  `θ = α/6 − α³/360 + α⁵/15120 + O(α⁷)`. The closed form suffers
  catastrophic cancellation in that range: at `α = 1e-6` it loses ~0.16%
  while the series is exact to machine precision.
- `α ≥ 1e-3` uses `1/tanh(α/2) − 2/α`, which saturates cleanly (`tanh`
  reaches 1.0 around `α ≈ 40`, so no overflow).
- Negative optical thickness raises `ValueError`; `α = inf` returns `1.0`.
- `θ` is precomputed once per run as a `(NTC, N_HALF)` array
  (`Config.theta_sc`) and reused by the sweep and by the scalar-flux
  integration, so the `tanh` cost is paid once.

## 6. Selecting a scheme

JSON / `inputs.py`:

```json
{
  "SPATIAL_SCHEME": "SC"
}
```

Accepted values: `"DD"`, `"STEP"`, `"SC"` (case-insensitive;
`"step_characteristic"` is an alias). Omitting the field means `"DD"`.
An invalid value raises `ValueError` at configuration time.

Interactive wizard (`nts-1d-run --manual` and `nts-1d-config`) asks, right
after the quadrature order:

```text
Spatial scheme (DD / STEP / SC) [DD]:
```

`Config.SPATIAL_SCHEME` is the single source of truth: `Config.method`
is a read-only property that parses it, so the string written to JSON and
the enum used by the solver cannot diverge.

## 7. Scalar flux

The scalar flux uses the cell averages of the selected scheme:

$$
\phi_i = \sum_{m>0} w_m\left(\bar{\psi}^{+}_{m,i}
+ \bar{\psi}^{-}_{m,i}\right).
$$

`ψ̄` is reconstructed from the two interface values after each sweep, so
no cell-average arrays are stored. `angular_flux[k, m]` keeps its historical
meaning `ω_m(ψ̄⁺ + ψ̄⁻)`, which is what `nts-1d-plot --kind angular` shows.

## 8. Reference results

20 cm homogeneous slab, vacuum, `σt = 1.0`, `σs0 = 0.9`, `νσf = 0.11`,
`TOL_K = 1e-6`:

| N | DD | STEP | SC |
|---|---|---|---|
| S2 | 1.024641 | 1.014232 | 1.024023 |
| S4 | 1.026509 | 1.017327 | 1.025885 |
| S8 | 1.026676 | 1.017843 | 1.026054 |

Mesh convergence (S8):

| Cells | DD | STEP | SC |
|---|---|---|---|
| 25 | 1.026539 | 0.994259 | 1.017809 |
| 50 | 1.026649 | 1.009516 | 1.024237 |
| 100 | 1.026676 | 1.017843 | 1.026054 |
| 200 | 1.026683 | 1.022198 | 1.026526 |

DD and SC converge to `≈1.026689`; STEP converges to the same limit but at
first order, so at practical meshes it sits ~0.9% (100 cells) or ~0.45%
(200 cells) below DD. **This is the expected behaviour of the step
approximation, not a defect.**

Scheme-independent check: a slab with reflective boundaries on both sides
has no leakage and `k_eff = νΣf/Σa`. All three schemes return
`0.5999998` for the analytic `0.6` case.

## 9. Numerical behaviour and limitations

There is **no clipping, positivity constraint or artificial correction** of
the fluxes. Each scheme shows its natural behaviour:

| Cell, `α = 50`, `ψ_in = 1`, `S = 0` | `ψ_out` | `ψ̄` |
|---|---|---|
| DD | −0.923 | +0.038 |
| STEP | +0.0196 | +0.0196 |
| SC | 0.0 (to round-off) | +0.020 |

- DD may produce negative angular fluxes in optically thick cells or strong
  gradients. Refine the mesh if that happens.
- STEP is monotone positive but diffusive: it overestimates the flux around
  localised sources.
- SC stays close to DD and is much better behaved than DD for thick cells,
  but it is not "exact attenuation": its `ψ_out` is a linear-source
  approximation and does not reproduce `ψ_in·e^{−α}` for large `α`.
- None of the three schemes accelerates convergence; the inner iteration
  count is similar (SC and DD are slightly higher than STEP).
- Differences between schemes are physical discretization differences. Only
  DD is bit-for-bit backward compatible.

## 10. Validation

`tests/test_spatial_schemes.py` covers:

- cell balance for the three schemes on a random grid (relative residual
  `< 1e-9`);
- consistency between `cell_average()` and the average implied by the sweep;
- `θ` limits (`α = 0`, `inf`, negative, NaN), series/closed-form continuity,
  monotonicity and range;
- SC → DD for thin cells and SC average → STEP convention for thick cells;
- `|μ|` normalisation, `|μ| = 0` rejection and unknown-scheme rejection;
- no artificial positivity (thick-cell sign reported, not corrected);
- DD regression against the frozen pre-refactor results;
- reflective infinite medium for all three (`k_eff = 0.6`);
- the 20 cm benchmark for all three;
- solver-level per-cell balance for all three;
- vacuum and reflective boundaries for all three.

```bash
uv run nts-test
```

## 11. Internal references

- `solvers/runners/NTS_DD_1D.py` — `Method`, kernels, `cell_out`,
  `cell_average`, `Config.theta_sc`.
- `tests/test_spatial_schemes.py` — scheme tests.
- `doc/MULTIPLICATIVE_MEDIA_EN.md` — fission modes and `k_eff`.
- `doc/SPATIAL_SCHEMES.md` — Spanish version.
