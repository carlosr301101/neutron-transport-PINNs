# Power calculation and normalization (1D)

Guide to the power calculation and scale factor of the 1D solver
(`POWER_KW`), including post-hoc normalization of an `output_1d_###.json`.

> Spanish version: [CALCULO_NORMALIZACION_1D.md](CALCULO_NORMALIZACION_1D.md).

## 1. Quantities and convention

| Symbol | Meaning | Units |
|---|---|---|
| `φ_i` | scalar flux in cell `i` (angular average) | n/(cm²·s) |
| `Σf,i` | macroscopic fission cross section | cm⁻¹ |
| `E_f` | recoverable energy per fission | MeV/fission |
| `A` | slab cross-sectional area | cm² |
| `Δx_i` | cell width | cm |

`φ` is the **angular average**, not the integral:

```text
φ_i = ½ Σ_{m>0} ω_m (ψ̄⁺_{i,m} + ψ̄⁻_{i,m}),    Σ_full ω = 2
```

That is why the physical fission rate carries a factor 2:
`2 Σ Σf φ Δx`.

`Σf` comes from `SIGMA_F`; if absent, it is derived from `NU_SIGF / NU`,
where `NU` is the number of neutrons per fission. If both are missing,
`NU = 2.49` (U-238 fast fission) is used with a warning; `SIGMA_F` wins.

## 2. Unnormalized power

```text
P̃ = E_f[MeV] · 1.602176634e-13 [J/MeV] · A[cm²] · 2 Σ_i Σf,i φ̃_i Δx_i   [W]
```

The `1.602176634e-13` factor converts MeV to joules. Without it `P̃` is not
in watts; without the `2`, the power is half of the physical value.

## 3. Scale factor

```text
C_N = P_target / P̃
```

`P_target` is in watts (`POWER_KW · 1e3`).

## 4. Scaling the state

All fluxes are multiplied by `C_N`, so the scalar and angular fluxes stay
consistent:

```text
φ_i^N = C_N · φ̃_i
ψ_{i,m}^N = C_N · ψ̃_{i,m}
```

In the code, `_scale_state` scales `scalar_flux`, `PSI_RIGHT`, `PSI_LEFT`
and `angular_flux` by the same factor.

`k_eff` is **unchanged**: normalization only fixes the flux amplitude, not
the shape or the eigenvalue.

## 5. Modes

- `eigenvalue`: after `k_eff` converges; the amplitude was arbitrary and
  `C_N` fixes it.
- `fixed_source` and `driven`: after the flux converges; `C_N` rescales the
  source-driven solution.
- `fixed_k`: same as `fixed_source`.

## 6. User inputs

When running the solver (config or wizard):

| Input | Field / prompt | Required | Units |
|---|---|---|---|
| Target power | `POWER_KW` / `Power [kW]` | yes | kW |
| Energy per fission | `E_F_MEV` / `E_f [MeV/fission]` | no (200) | MeV/fission |
| Area | `AREA_CM2` / `Cross-sectional area [cm^2]` | no (1) | cm² |
| Conversion | `nu` or `sigma_f` | yes | — |
| `NU` | `nu (neutrons/fission)` | if `nu` (default 2.49) | neutrons/fission |
| `SIGMA_F` | `Sigma_f Zone i` | if `sigma_f` | cm⁻¹ |
| `NU_SIGF` | `nu*Sigma_f Zone i` | yes | cm⁻¹ |

When normalizing an existing JSON (`nts-1d-normalize`):

| Input | Flag | Required | Units |
|---|---|---|---|
| Input JSON | `source` (positional) | yes | path |
| Target power | `--power-kw` | **yes** | kW |
| `E_f` | `--ef-mev` | no (config) | MeV/fission |
| Area | `--area-cm2` | no (config) | cm² |
| `NU` | `--nu` | only if no `SIGMA_F`/`NU` (default 2.49) | neutrons/fission |
| Runs | `--run NAME\|INDEX` | no (all) | — |
| Output | `-o` | no (`<stem>_normalized.json`) | path |

## 7. Example (20 cm benchmark)

`L=20 cm`, `Σt=1.0`, `Σs=0.9`, `νΣf=0.11`, `NU=2.4`, `E_f=200 MeV`,
`A=1 cm²`, `POWER_KW=10`.

With the eigenvalue flux normalized to maximum 1:

```text
Σ_i Σf,i φ̃_i Δx_i = 0.620653
P̃ = 200 · 1.602176634e-13 · 1 · 2 · 0.620653 = 3.9776e-11 W
C_N = 10000 / 3.9776e-11 = 2.5141e14
```

After scaling, `2 Σ Σf φ Δx · E_f · 1.602e-13 = 10,000 W`.

## 8. Commands

```bash
# Normalize during the run
uv run nts-1d-run --json config.json --excel

# Normalize an existing output
uv run nts-1d-normalize outputs/results/output_1d_003.json --power-kw 10
uv run nts-1d-normalize output_1d_003.json --power-kw 10 --nu 2.4 -o normalized.json

# Export the normalized result to Excel
uv run nts-1d-excel normalized.json
```

Each run in the JSON includes `power_w` (target power), `power_scale`
(`C_N`) and `power_unnormalized` (`P̃`).

## 9. Validation

- `POWER_KW > 0`; in `nts-1d-normalize`, `--power-kw` is required.
- `E_F_MEV > 0`, `AREA_CM2 > 0`, `NU > 0`.
- `Σf ≥ 0` and at least one zone with `Σf > 0`.
- If both `SIGMA_F` and `NU` exist, `SIGMA_F` wins.
- `NC`, `HR` and `IZL` must rebuild the mesh and expand `Σf`.
- A run without `scalar_flux` or with a zero fission integral is skipped
  with a warning.
