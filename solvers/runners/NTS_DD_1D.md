# Diamond Difference (`DD`)

Reference card for the default spatial discretization of the 1D S_N solver.

- Module: [`NTS_DD_1D.py`](NTS_DD_1D.py)
- Entry point: `nts-1d-run-dd`
- Bilingual overview: [doc/SPATIAL_SCHEMES_EN.md](../../doc/SPATIAL_SCHEMES_EN.md)
  (Spanish: [doc/SPATIAL_SCHEMES.md](../../doc/SPATIAL_SCHEMES.md))

## Cell equations

With `a = |mu| / dx`, the cell balance

```
a * (psi_out - psi_in) + Sigma_t * psi_bar = S
```

is closed with the arithmetic mean:

```
psi_out = [(a - Sigma_t/2) * psi_in + S] / (a + Sigma_t/2)
psi_bar = (psi_in + psi_out) / 2
```

`S` is the full isotropic right-hand side
`1/2 * (Q + Sigma_s * Phi) + fission_source`; the `1/2` factors are already
included, do not add another one.

## Properties

- Second order in `dx`.
- Bit-for-bit compatible with the pre-refactor solver: the 20 cm benchmark
  gives `k_eff = 1.0266764379437188` (S8, 100 cells).
- Can produce **negative angular fluxes** in optically thick cells
  (`Sigma_t * dx / |mu|` large). No clipping is applied.
- Reference values (20 cm, vacuum, `Sigma_t=1.0`, `Sigma_s=0.9`,
  `nu*Sigma_f=0.11`):

| N | `k_eff` (100 cells) |
|---|---|
| S2 | 1.024641 |
| S4 | 1.026509 |
| S8 | 1.026676 |

| Cells (S8) | `k_eff` |
|---|---|
| 25 | 1.026539 |
| 50 | 1.026649 |
| 100 | 1.026676 |
| 200 | 1.026683 |

## Code

```python
class DiamondDifference:
    method = Method.DD

    def prepare(self, config):
        return None                      # no per-run data

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None):
        a = mu / dx
        return ((a - 0.5 * sigma_t) * psi_in + source) / (a + 0.5 * sigma_t)

    def cell_average(self, psi_in, psi_out, sigma_t, dx, mu, theta=None):
        return 0.5 * (psi_in + psi_out)


SCHEME = DiamondDifference()


def solve(config, **kwargs):
    return Runner(config, scheme=SCHEME, **kwargs)()
```

This module is also the **compatibility facade**: it re-exports `Config`,
`Runner`, `Method`, `cell_out`, `cell_average` and
`theta_step_characteristic`, so existing imports from
`solvers.runners.NTS_DD_1D` keep working.

## Selecting it

```json
{ "SPATIAL_SCHEME": "DD" }
```

`DD` is the default when the field is omitted, and the scheme used by
`nts-1d-run` when the config does not choose another one. The wizard asks
`Spatial scheme (DD / STEP / SC) [DD]:`; `nts-1d-run-dd` forces it and
overrides the file with a warning.

## Reported values

`scalar_flux` is the angular average `φ = 1/2 Σ ω ψ` (the N weights sum
to 2). `angular_flux` is `(NTC, N)`, one cell-averaged value per cell and
direction; `scalar_flux_contribution[k, m] = 1/2 ω_m(ψ̄⁺+ψ̄⁻)` sums to
`φ`. `miu` and `omega` are exported with each run.

## Tests

`tests/test_spatial_schemes.py` covers the cell balance, the DD regression
(`1.0266764379437188`) and the dd/step/sc comparison. `tests/test_entrypoints.py`
covers the forced entry point.
