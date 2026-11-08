# Cálculo y normalización de potencia (1D)

Guía del cálculo de potencia y de la constante de escala del solver 1D
(`POWER_KW`), incluyendo la normalización posterior de un `output_1d_###.json`.

> Versión en inglés: [CALCULO_NORMALIZACION_1D_EN.md](CALCULO_NORMALIZACION_1D_EN.md).

## 1. Magnitudes y convención

| Símbolo | Significado | Unidades |
|---|---|---|
| `φ_i` | flujo escalar en la celda `i` (media angular) | n/(cm²·s) |
| `Σf,i` | sección eficaz macroscópica de fisión | cm⁻¹ |
| `E_f` | energía recuperable por fisión | MeV/fisión |
| `A` | área transversal de la placa | cm² |
| `Δx_i` | ancho de la celda `i` | cm |

`φ` es la **media angular**, no la integral:

```text
φ_i = ½ Σ_{m>0} ω_m (ψ̄⁺_{i,m} + ψ̄⁻_{i,m}),    Σ_full ω = 2
```

Por eso la tasa de fisión física lleva un factor 2: `2 Σ Σf φ Δx`.

`Σf` se toma de `SIGMA_F`; si no está, se deriva de `NU_SIGF / NU`, donde
`NU` es el número de neutrones por fisión. Si faltan `SIGMA_F` y `NU`, se
usa `NU = 2.49` (U-238, fisión rápida) y se avisa; `SIGMA_F` tiene prioridad.

## 2. Potencia sin normalizar

```text
P̃ = E_f[MeV] · 1.602176634e-13 [J/MeV] · A[cm²] · 2 Σ_i Σf,i φ̃_i Δx_i   [W]
```

El factor `1.602176634e-13` convierte MeV a julios. Sin él, `P̃` no está en
vatios; sin el `2`, la potencia sale a la mitad.

## 3. Constante de escala

```text
C_N = P_objetivo / P̃
```

`P_objetivo` se expresa en vatios (`POWER_KW · 1e3`).

## 4. Escalado del estado

Se multiplican por `C_N` todos los flujos, para que el escalar y los
angulares sigan siendo consistentes:

```text
φ_i^N = C_N · φ̃_i
ψ_{i,m}^N = C_N · ψ̃_{i,m}
```

En el código esto lo hace `_scale_state`, que escala `scalar_flux`,
`PSI_RIGHT`, `PSI_LEFT` y `angular_flux` por el mismo factor.

`k_eff` **no cambia**: la normalización solo fija la amplitud del flujo, no
la forma ni el autovalor.

## 5. Modos de aplicación

- `eigenvalue`: tras converger `k_eff`; la amplitud era arbitraria y `C_N` la fija.
- `fixed_source` y `driven`: tras converger el flujo; `C_N` reescala la
  solución del problema con fuente.
- `fixed_k`: igual que `fixed_source`.

## 6. Datos que introduce el usuario

Al correr el solver (config o asistente):

| Dato | Campo / prompt | Obligatorio | Unidades |
|---|---|---|---|
| Potencia objetivo | `POWER_KW` / `Power [kW]` | sí | kW |
| Energía por fisión | `E_F_MEV` / `E_f [MeV/fission]` | no (200) | MeV/fisión |
| Área | `AREA_CM2` / `Cross-sectional area [cm^2]` | no (1) | cm² |
| Conversión | `nu` o `sigma_f` | sí | — |
| `NU` | `nu (neutrons/fission)` | si eligió `nu` (default 2.49) | neutrones/fisión |
| `SIGMA_F` | `Sigma_f Zone i` | si eligió `sigma_f` | cm⁻¹ |
| `NU_SIGF` | `nu*Sigma_f Zone i` | sí | cm⁻¹ |

Al normalizar un JSON existente (`nts-1d-normalize`):

| Dato | Flag | Obligatorio | Unidades |
|---|---|---|---|
| JSON de entrada | `source` (posicional) | sí | ruta |
| Potencia objetivo | `--power-kw` | **sí** | kW |
| `E_f` | `--ef-mev` | no (config) | MeV/fisión |
| Área | `--area-cm2` | no (config) | cm² |
| `NU` | `--nu` | solo si no hay `SIGMA_F` ni `NU` (default 2.49) | neutrones/fisión |
| Runs | `--run NAME\|INDEX` | no (todos) | — |
| Salida | `-o` | no (`<stem>_normalized.json`) | ruta |

## 7. Ejemplo (benchmark de 20 cm)

`L=20 cm`, `Σt=1.0`, `Σs=0.9`, `νΣf=0.11`, `NU=2.4`, `E_f=200 MeV`,
`A=1 cm²`, `POWER_KW=10`.

Con el flujo del autovalor normalizado a máximo 1:

```text
Σ_i Σf,i φ̃_i Δx_i = 0.620653
P̃ = 200 · 1.602176634e-13 · 1 · 2 · 0.620653 = 3.9776e-11 W
C_N = 10000 / 3.9776e-11 = 2.5141e14
```

Tras escalar, `2 Σ Σf φ Δx · E_f · 1.602e-13 = 10 000 W`.

## 8. Comandos

```bash
# Normalizar durante la corrida
uv run nts-1d-run --json config.json --excel

# Normalizar un output existente
uv run nts-1d-normalize outputs/results/output_1d_003.json --power-kw 10
uv run nts-1d-normalize output_1d_003.json --power-kw 10 --nu 2.4 -o normalizado.json

# Exportar el resultado normalizado a Excel
uv run nts-1d-excel normalizado.json
```

El JSON de cada run incluye `power_w` (potencia objetivo), `power_scale`
(`C_N`) y `power_unnormalized` (`P̃`).

## 9. Validaciones

- `POWER_KW > 0`; en `nts-1d-normalize`, `--power-kw` es obligatorio.
- `E_F_MEV > 0`, `AREA_CM2 > 0`, `NU > 0`.
- `Σf ≥ 0` y al menos una zona con `Σf > 0`.
- Si existen `SIGMA_F` y `NU`, se usa `SIGMA_F`.
- `NC`, `HR` e `IZL` deben permitir reconstruir la malla y expandir `Σf`.
- Un run sin `scalar_flux` o con integral de fisión nula se omite con aviso.
