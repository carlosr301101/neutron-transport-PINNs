# Step Characteristics (`SC`)

Reference card for the characteristic-weighted spatial discretization of the
1D S_N solver.

- Module: [`NTS_SC_1D.py`](NTS_SC_1D.py)
- Entry point: `nts-1d-run-sc`
- Bilingual overview: [doc/SPATIAL_SCHEMES_EN.md](../../doc/SPATIAL_SCHEMES_EN.md)
  (Spanish: [doc/SPATIAL_SCHEMES.md](../../doc/SPATIAL_SCHEMES.md))

## Cell equations

With `a = |mu| / dx` and the optical thickness `alpha = Sigma_t * dx / |mu|`:

```
theta   = coth(alpha/2) - 2/alpha
psi_bar = (1 + theta)/2 * psi_out + (1 - theta)/2 * psi_in
psi_out = [(a - Sigma_t*(1 - theta)/2) * psi_in + S]
          / [a + Sigma_t*(1 + theta)/2]
```

`theta` is a convex weight in `[0, 1)`: it tends to `0` for thin cells
(SC -> DD) and to `1` for thick cells (the average -> the STEP convention).
`S` is the full isotropic right-hand side with its `1/2` factors included.

## Numerical stability

- `alpha = 0` returns `theta = 0`.
- `alpha < 1e-3` uses the series
  `alpha/6 - alpha^3/360 + alpha^5/15120`. The closed form loses ~0.16% to
  cancellation at `alpha = 1e-6`; the series is exact to machine precision.
- `alpha >= 1e-3` uses `1/tanh(alpha/2) - 2/alpha`, which saturates without
  overflow.
- Negative optical thickness raises `ValueError`; `alpha = inf` returns `1.0`.

## Properties

- Second order in `dx`; closest to DD on coarse meshes.
- `theta` is precomputed once per run in `prepare()` as an
  `(NTC, N_HALF)` array, shared by the sweep and the scalar-flux
  integration.
- More robust than DD in thick cells, but **not** "exact attenuation": its
  `psi_out` is a linear-source approximation and does not reproduce
  `psi_in * exp(-alpha)` for large `alpha`. Slightly negative values can
  appear in the far tail of very thick cells; they are reported, not clipped.
- Reference values (20 cm, vacuum, `Sigma_t=1.0`, `Sigma_s=0.9`,
  `nu*Sigma_f=0.11`):

| N | `k_eff` (100 cells) |
|---|---|
| S2 | 1.024023 |
| S4 | 1.025885 |
| S8 | 1.026054 |

| Cells (S8) | `k_eff` |
|---|---|
| 25 | 1.017809 |
| 50 | 1.024237 |
| 100 | 1.026054 |
| 200 | 1.026526 |

## Code

```python
class StepCharacteristic:
    method = Method.STEP_CHARACTERISTIC

    def prepare(self, config):
        # theta = coth(alpha/2) - 2/alpha, shape (NTC, N_HALF)
        ...

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None):
        if theta is None:
            theta = theta_step_characteristic(sigma_t * dx / mu)
        a = mu / dx
        return ((a - 0.5 * sigma_t * (1 - theta)) * psi_in + source) / (
            a + 0.5 * sigma_t * (1 + theta)
        )

    def cell_average(self, psi_in, psi_out, sigma_t, dx, mu, theta=None):
        if theta is None:
            theta = theta_step_characteristic(sigma_t * dx / mu)
        return 0.5 * (1 + theta) * psi_out + 0.5 * (1 - theta) * psi_in


SCHEME = StepCharacteristic()


def solve(config, **kwargs):
    return Runner(config, scheme=SCHEME, **kwargs)()
```

## Selecting it

```json
{ "SPATIAL_SCHEME": "SC" }
```

`nts-1d-run-sc` forces it regardless of the file and prints
`SPATIAL_SCHEME=... overridden by this entry point (using SC)`. The wizard
accepts `SC` at the `Spatial scheme` prompt.

## Reported values

`scalar_flux` is the angular average `φ = 1/2 Σ ω ψ` (the N weights sum
to 2). `angular_flux` is `(NTC, N)`, one cell-averaged value per cell and
direction; `miu` and `omega` are exported with each run.

## Tests

`tests/test_spatial_schemes.py` covers `theta` (limits, series/closed-form
continuity, monotonicity, range), the SC -> DD and SC -> STEP limits, the
`prepare()` shape and the benchmark tolerance (within 1e-3 of DD).
`tests/test_entrypoints.py` covers the forced entry point.
