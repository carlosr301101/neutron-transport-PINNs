# Step Difference (`STEP`)

Reference card for the implicit upwind spatial discretization of the 1D S_N
solver.

- Module: [`NTS_STEP_1D.py`](NTS_STEP_1D.py)
- Entry point: `nts-1d-run-step`
- Bilingual overview: [doc/SPATIAL_SCHEMES_EN.md](../../doc/SPATIAL_SCHEMES_EN.md)
  (Spanish: [doc/SPATIAL_SCHEMES.md](../../doc/SPATIAL_SCHEMES.md))

## Cell equations

With `a = |mu| / dx`:

```
psi_out = (a * psi_in + S) / (a + Sigma_t)
psi_bar = psi_out                    # downstream (outflow) face value
```

The cell average is the **downstream** interface value. This is the implicit
upwind convention: it is stable and positive for any optical thickness. The
explicit variant (`psi_bar = psi_in`) is intentionally not implemented.

`S` is the full isotropic right-hand side with its `1/2` factors already
included.

## Properties

- **First order** in `dx`. The error is visible on coarse meshes: at 100
  cells it sits ~0.9% below DD; at 200 cells, ~0.45%.
- Unconditionally positive: angular and scalar fluxes cannot go negative.
- Diffusive: it smears steep gradients and overestimates the flux around
  localised sources. This is the expected behaviour of the scheme, not a bug.
- Reference values (20 cm, vacuum, `Sigma_t=1.0`, `Sigma_s=0.9`,
  `nu*Sigma_f=0.11`):

| N | `k_eff` (100 cells) |
|---|---|
| S2 | 1.014232 |
| S4 | 1.017327 |
| S8 | 1.017843 |

| Cells (S8) | `k_eff` |
|---|---|
| 25 | 0.994259 |
| 50 | 1.009516 |
| 100 | 1.017843 |
| 200 | 1.022198 |

## Code

```python
class Step:
    method = Method.STEP

    def prepare(self, config):
        return None                      # no per-run data

    def cell_out(self, psi_in, source, sigma_t, dx, mu, theta=None):
        a = mu / dx
        return (a * psi_in + source) / (a + sigma_t)

    def cell_average(self, psi_in, psi_out, sigma_t, dx, mu, theta=None):
        return psi_out


SCHEME = Step()


def solve(config, **kwargs):
    return Runner(config, scheme=SCHEME, **kwargs)()
```

## Selecting it

```json
{ "SPATIAL_SCHEME": "STEP" }
```

`nts-1d-run-step` forces it regardless of the file and prints
`SPATIAL_SCHEME=... overridden by this entry point (using STEP)`. The wizard
accepts `STEP` at the `Spatial scheme` prompt.

## Tests

`tests/test_spatial_schemes.py` checks the cell balance, the positivity of
thick cells and the benchmark tolerance (within 2e-2 of DD).
`tests/test_entrypoints.py` covers the forced entry point.
