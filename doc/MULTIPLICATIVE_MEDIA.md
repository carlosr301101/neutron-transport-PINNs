# Medios multiplicativos y factor efectivo de multiplicación (`k_eff`)

Guía del modo multiplicativo de los solvers 1D (`NTS_DD_1D.py`,
`NTS_STEP_1D.py`, `NTS_SC_1D.py`, sobre un motor compartido en `config.py`
y `runner.py`).

> **Alcance:** esta capacidad es exclusiva del solver 1D en Python. Los
> solvers 2D en C (`NTS_DD`, `NTS_LD`, `NTS_STEP`, `NTS_RM_CN`,
> `NTS_RM_LLN`) siguen siendo de fuente fija y no aceptan `NU_SIGF` ni
> `k_eff`.

## 1. Ecuación resuelta

Para un grupo de energía, scattering isotrópico y fisión isotrópica:

$$
\mu_m \frac{d\Psi_m(x)}{dx} + \Sigma_t(x)\Psi_m(x)
= \frac12\left[\Sigma_s(x) + \frac{\nu\Sigma_f(x)}{k}\right]\Phi(x)
+ \frac12 Q(x),
\qquad m = 1,\dots,N
$$

con

$$
\Phi(x) = \sum_{m>0} w_m \left[\Psi_m^+(x) + \Psi_m^-(x)\right].
$$

Convenciones del código:

- `NU_SIGF` es **νΣf** (cm⁻¹), no `4π·νΣf`. El factor `1/2` de la fuente
  isotrópica ya está incluido en la ecuación y en el barrido.
- `SIGMA_F` es **Σf** (cm⁻¹). Es opcional y solo se usa para normalizar la
  potencia.
- Si se da `NU_SIGF` pero no `SIGMA_F`, la normalización de potencia usa
  `Σf = νΣf / NU`, donde `NU` es el número de neutrones por fisión.
- `Q` es la fuente externa por región y `bound_left`/`bound_right` son los
  flujos entrantes en las fronteras.

## 2. Los cuatro modos

| `MODE` | `NU_SIGF` | `K_EFF` | Fuente | Qué resuelve |
|---|---|---|---|---|
| `fixed_source` | 0 | — | `Q` o flujo entrante | Transporte sin fisión (comportamiento histórico) |
| `eigenvalue` | > 0 | — | `Q = 0`, fronteras homogéneas | Calcula `k_eff` y la forma fundamental |
| `fixed_k` | > 0 | > 0 | opcional | Fisión escalada por un `k` impuesto |
| `driven` | > 0 | 1 (fijo) | obligatoria | Problema físico con fuente y fisión |

### 2.1 `fixed_source`

Es el modo que ya existía. `NU_SIGF = 0`, la fuente es `Q` y/o el flujo
entrante. No calcula `k_eff`.

### 2.2 `eigenvalue`

Resuelve el problema **homogéneo**:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \frac{\nu\Sigma_f}{k}\right]\Phi,
\qquad Q = 0,
$$

y busca el mayor `k` para el que existe una solución no trivial. Ese es el
factor efectivo de multiplicación. La amplitud del flujo es arbitraria; el
solver la normaliza (máximo = 1) y, si se pide, la reescala a una potencia.

**Condición:** `Q = 0` y flujo entrante nulo. Las fronteras pueden ser de
vacío o reflexivas, porque ambas son homogéneas. Si hay fuente externa, el
problema deja de ser un autovalor y hay que usar `fixed_k` o `driven`.

### 2.3 `fixed_k`

Resuelve la ecuación con un `k` impuesto:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \frac{\nu\Sigma_f}{k_{\text{impuesto}}}\right]\Phi
+ \frac12 Q.
$$

- **Con fuente** (`Q ≠ 0` o flujo entrante): problema lineal con solución
  única para `k ≠ k*`; la amplitud la fija la fuente.
- **Sin fuente**: problema homogéneo. Solo en `k = k*` hay una solución
  estacionaria no trivial. Si `k ≠ k*`, la solución estacionaria es cero;
  el solver normaliza y reporta `k_balance = P/(A+L)`, que es el `k`
  crítico estimado a partir de la forma obtenida.

`fixed_k` es útil para estudios paramétricos y para verificar el autovalor:
si se corre en `k = k*`, la forma debe quedar estacionaria y
`k_balance ≈ k*`.

### 2.4 `driven`

Es el problema físico con fuente. Impone `k = 1` (no se divide la fisión
por `k`) y exige `Q ≠ 0` o flujo entrante:

$$
\mu_m \frac{d\Psi_m}{dx} + \Sigma_t\Psi_m
= \frac12\left[\Sigma_s + \nu\Sigma_f\right]\Phi + \frac12 Q.
$$

Si el sistema es subcrítico (`k_eff < 1`), la solución es finita y única.
Si es supercrítico (`k_eff > 1`), el flujo crece sin límite y la iteración
no converge. El `k_eff` del sistema se calcula aparte con `eigenvalue`; en
`driven` se reporta `k_balance` como diagnóstico.

> **No mezclar `k = k*` con fuente.** En `k = k*` el operador es singular:
> una fuente en un sistema crítico no tiene estado estacionario (el flujo
> crece). El código rechaza `MODE='driven'` con `K_EFF ≠ 1` y
> `MODE='eigenvalue'` con fuente.

## 3. Configuración

Campos nuevos en los diccionarios de `outputs/inputs/inputs.py`:

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `NU_SIGF` | lista por zona | `[0.0]*NZ` | νΣf en cm⁻¹ |
| `SIGMA_F` | lista por zona | `None` | Σf en cm⁻¹ (para potencia) |
| `MODE` | str | inferido | `fixed_source`, `eigenvalue`, `fixed_k`, `driven` |
| `K_EFF` | float | `None` | `k` impuesto; solo `fixed_k` |
| `TOL_K` | float | `1e-6` | tolerancia de convergencia de `k_eff` |
| `MAX_OUTER` | int | `200` | iteraciones exteriores del power iteration |
| `K0` | float | `None` | guess inicial; `None` → `∫νΣf/∫Σa` |
| `POWER_KW` | float | `None` | activa la normalización de potencia |
| `E_F_MEV` | float | `200.0` | energía recuperable por fisión |
| `NU` | float | `None` | neutrones por fisión (si no hay `SIGMA_F`) |
| `AREA_CM2` | float | `1.0` | área transversal de la placa |

Si `MODE` se omite, el solver infiere:

- `NU_SIGF` todo cero → `fixed_source`.
- `NU_SIGF > 0` y `K_EFF = None` → `eigenvalue`.
- `NU_SIGF > 0` y `K_EFF` dado → `fixed_k`.

Para evitar ambigüedades se recomienda declarar `MODE` explícitamente.

### Ejemplo: benchmark de 20 cm

Placa homogénea de 20 cm, vacío en ambas caras, σt = 1.0 cm⁻¹,
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

Ejecución:

```bash
uv run nts-1d-run
```

Salida esperada (S8, 100 celdas):

```text
--- STARTING CALCULATION ---
Source: outputs/inputs/inputs.py | run config_dict
EIGENVALUE CONVERGED: k_eff = 1.026676...
k_balance (P/(A+L)) = 1.026677...
```

La línea `Source:` muestra el archivo del que salió la configuración y el
nombre del run (`interactive wizard | run manual` para `--manual`,
`<archivo>.json | run json_config_001` para `--json`). Se omite cuando el
`Runner` se usa directamente desde Python.

### 3.1 Configuración manual por consola

```bash
uv run nts-1d-run --manual
# equivalente
uv run nts run-1d --manual
```

El asistente pregunta, paso a paso:

1. geometría (`NC`, `HR`, `IZL`) y materiales (`SCT`, `SCS`);
2. cuadratura `N` (2, 4, 6, 8; default 8);
3. si hay fisión: `NU_SIGF` por zona, `MODE`, `K_EFF` (solo `fixed_k`),
   `TOL_K`, `MAX_OUTER`, `K0`;
4. normalización de potencia opcional (`POWER_KW`, `E_F_MEV`, `AREA_CM2` y
   conversión con `NU` o `SIGMA_F`);
5. `Q` por región (se omite en `eigenvalue`, donde vale 0);
6. fronteras reflexivas/vacío y flujo entrante por dirección (se fuerza a 0
   en `eigenvalue`);
7. resumen de la configuración y confirmación `Run? (y/n) [y]`.

Validaciones del asistente:

- `NU_SIGF ≥ 0`;
- `fixed_k` exige `K_EFF > 0`;
- `driven` exige `Q ≠ 0` o flujo entrante;
- `POWER_KW` exige `NU` o `SIGMA_F`;
- `IZL` en `[1, num_zones]`;
- `N` par y tabulado (si no, se avisa del fallback a S2).

### 3.2 Carga desde JSON

```bash
uv run nts-1d-run --json config_multiplicativo.json
```

El archivo puede ser un objeto o una lista de objetos con las mismas claves
que un dict de `inputs.py`. Ejemplo para el benchmark:

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

`--manual`, `--json` y `-c` son mutuamente excluyentes. Cada run guarda su
`configuration` efectiva en el JSON de salida; `nts-1d-data` y
`sweep_kpis.py` la usan, así que no hace falta que el `config_name` exista
en `outputs/inputs/inputs.py`.

### 3.3 Generador de configuración con placeholders

```bash
uv run nts-1d-config -o outputs/inputs/config_1d_001.json
```

Es el mismo asistente que `--manual`, pero escribe un JSON en vez de
ejecutar. En los campos físicos de tipo float puedes escribir un número o
un placeholder:

```text
Sigma_Scattering Zone 1 (number or placeholder, e.g. kk): kk
nu*Sigma_f Zone 1 [cm^-1] (number or placeholder, e.g. mm): mm
```

El JSON resultante contiene:

```json
{
  "SCS": ["kk"],
  "NU_SIGF": ["mm"],
  "MODE": "eigenvalue",
  "TOL_K": 1e-6
}
```

Expansión y ejecución:

```bash
uv run nts-generate --json outputs/inputs/config_1d_001.json \
  --place-holder kk 0.1 0.95 0.05 \
  --place-holder mm 0.05 0.20 0.05 \
  -o outputs/inputs/inputs_1d.json

uv run nts-1d-run --json outputs/inputs/inputs_1d.json
```

- `-o .json` escribe una lista de configs; `-o .py` escribe
  `config_dict_###` (`inputs.py`).
- Sin `--json`, `nts-generate` sigue leyendo
  `outputs/inputs/inputs_placeholder.py`.
- Los placeholders se combinan en paralelo por índice (longitud mínima).
- Solo se redondean los valores inyectados; `TOL_K`, `K0`, etc. se
  conservan.
- `NC` y `HR` admiten placeholders. `NC` debe expandirse a enteros
  positivos; `HR` a floats positivos. `N`, `IZL` y `MAX_OUTER` no admiten
  placeholders.

## 4. Algoritmo

### 4.1 Power iteration (`eigenvalue`)

1. `k ← k0` (`k0 = ∫νΣf dx / ∫(Σt−Σs) dx` si no se da).
2. `Φ ← 1` (guess plano positivo).
3. Repetir para `outer = 1..MAX_OUTER`:
   1. Congelar la fuente de fisión:
      `S_f = ½ νΣf Φ / k`.
   2. Iteración interna de scattering hasta que el cambio relativo de `Φ`
      sea menor que `min(epsilon, TOL_K)`.
   3. `P_new = ∫νΣf Φ_new dx`.
   4. `k_new = k · P_new / P_old`.
   5. Normalizar **todo** el estado (`Φ`, `Ψ⁺`, `Ψ⁻`, `angular_flux`).
   6. `P_old ← ∫νΣf Φ dx`.
   7. Parar si `|k_new − k| / |k_new| < TOL_K`.
4. Reportar `k_eff`, `k_balance` y el historial.

La tolerancia interna se ata a `TOL_K` para que el error de scattering no
sesgue `k_eff`.

### 4.2 `fixed_k`

1. `k ← K_EFF`.
2. En cada barrido: `S_f = ½ νΣf Φ / k`.
3. Si no hay fuente, normalizar el estado en cada iteración y avisar de que
   la amplitud es arbitraria.
4. Converger por flujo; reportar `k_balance`.

### 4.3 `driven`

Igual que `fixed_k` con `k = 1`, pero exige fuente externa. No normaliza: la
fuente fija la amplitud.

### 4.4 Balance global

Con el flujo convergido:

$$
P = \int \nu\Sigma_f \Phi\,dx,\qquad
A = \int (\Sigma_t-\Sigma_s)\Phi\,dx,\qquad
L = \text{fuga neta},
$$

$$
k_{\text{balance}} = \frac{P}{A+L}.
$$

La fuga neta se calcula como **saliente − entrante** en cada frontera. Con
fronteras reflexivas, `L = 0`; con vacío, `L` es la fuga saliente. En el
autovalor debe cumplirse `k_eff ≈ k_balance`.

## 5. Normalización por potencia

`k_eff` no depende de la escala del flujo. Para fijar la amplitud:

$$
P = A\,E_f\,(1.602176634\times10^{-13})
\int_0^L \Sigma_f \Phi\,dx,
$$

con `P` en W, `A` en cm², `E_f` en MeV/fisión y `Σf` en cm⁻¹. Si no se da
`SIGMA_F`, se usa `Σf = νΣf / NU`.

Ejemplo: `POWER_KW = 10`, `E_F_MEV = 200`, `NU = 2.4`, `AREA_CM2 = 1`.
El solver escala `Φ`, `Ψ⁺`, `Ψ⁻` y `angular_flux` por el mismo factor y
reporta `power_w` y `power_scale`.

> La convención `E_f = 200 MeV`, `ν = 2.4` y `A = 1 cm²` es una elección
> de trabajo. Si el curso usa otros valores, cámbialos en la configuración.

## 6. Benchmark de referencia

Datos: `L = 20 cm`, `σt = 1.0`, `σs0 = 0.9`, `νσf = 0.11`, vacío.

| Orden | `k_eff` (100 celdas, `TOL_K=1e-6`) |
|---|---|
| S2 | 1.024641 |
| S4 | 1.026509 |
| S8 | 1.026676 |

Convergencia en malla (S8):

| Celdas | `k_eff` |
|---|---|
| 25 | 1.026539 |
| 50 | 1.026649 |
| 100 | 1.026676 |
| 200 | 1.026683 |
| 400 | 1.026685 |

Con `epsilon`/`TOL_K` más finos los valores convergen a ~`1.026689`.

Contrastes:

- `k_inf = νΣf / (Σt − Σs) = 1.1` (cota superior).
- S2 analítico: `1.024654` (coincide con el numérico al orden de `1e-5`).
- Difusión P1: `1.026409` (mismo orden).
- El sistema es ligeramente supercrítico (`k_eff > 1`); es válido para un
  autovalor.

### Test exacto: medio infinito reflectivo

Con fronteras reflexivas en ambos lados no hay fuga y el flujo fundamental
es plano:

$$
k_{eff} = \frac{\nu\Sigma_f}{\Sigma_t-\Sigma_s}.
$$

Este caso se usa como test de aceptación (`tests/test_dd_1d_fission.py`).

## 7. Salida

Cada run de `output_1d_###.json` añade:

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

`nts-1d-data` añade `NU_SIGF`, `mode`, `k_eff` y `k_balance` a cada fila de
`datos.json`. `nts-1d-plot --x k_eff` permite graficar flujo contra `k_eff`;
`--x NU_SIGF` grafica contra νΣf.

### 7.1 Gráficos desde `output_1d`

`nts-1d-plot` lee el JSON crudo (`runs[]`), no solo `datos.json`:

```bash
# Ver los runs disponibles
uv run nts-1d-plot -r outputs/results/output_1d_016.json --list-runs

# Φ(x)
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind scalar --run manual

# Flujo angular: una línea por dirección, misma gráfica, colores y leyenda
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual --directions 0 1

# k_eff vs iteración exterior
uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind k-history --run manual

# Modo legado (datos.json)
uv run nts-1d-plot -i outputs/results/datos.json --x k_eff
```

Reglas:

- Si el fichero tiene más de un run, `--run NOMBRE|INDICE` es obligatorio;
  `--list-runs` muestra las opciones. `--run all` superpone todos los runs
  para `scalar`/`k-history`; `angular` exige exactamente uno.
- `angular_flux` se guarda como `ω_m(ψ⁺ + ψ⁻)`; la etiqueta del eje Y lo
  indica.
- `--kind k-history` solo funciona con `MODE=eigenvalue`; en los demás
  modos el historial está vacío.
- Salidas por defecto: `outputs/results/plots/scalar_flux.png`,
  `angular_flux.png`, `k_history.png`.

## 8. Validación

```bash
uv run nts-test -v
```

Tests incluidos:

- medio infinito reflectivo: `k = νΣf/Σa`;
- benchmark de 20 cm;
- `fixed_k` en `k*` contra el autovalor;
- `driven` subcrítico: `k_balance = 0.5`;
- normalización de potencia a 10 kW;
- regresión `NU_SIGF = 0`;
- fronteras mixtas (reflexiva/vacío) sin inyección artificial de flujo;
- inferencia de `MODE` cuando se omite;
- combinaciones de modo inválidas.

## 9. Trampas conocidas

1. **`4π`:** la skill `sn-spectral` usa `c = Σs/Σt + 4πν̄Σf/(kΣt)` por su
   convención. Aquí **no** va `4π`; la ecuación ya trae `1/2`.
2. **`eigenvalue` con fuente:** no es un autovalor. Usa `driven` o `fixed_k`.
3. **`k = k*` con fuente:** operador singular, sin estado estacionario.
4. **`fixed_k` sin fuente:** la amplitud es arbitraria; solo se obtiene una
   forma de modo y `k_balance`.
5. **Normalizar solo el flujo escalar:** rompe la consistencia con los
   flujos angulares. El solver escala todo el estado.
6. **DD con celdas ópticamente gruesas:** puede producir flujos negativos;
   refinar la malla.
7. **Power iteration lento:** si el *dominance ratio* está cerca de 1,
   aumentar `MAX_OUTER` o refinar; no es un bug.
8. **`NU_SIGF` vs `SIGMA_F` vs `NU`:** `NU_SIGF` es νΣf; `SIGMA_F` es Σf;
   `NU` solo se usa para convertir uno en otro al normalizar potencia.
9. **Peso N=6:** corregido a `0.4679139345726910` en `cuadraturas.py`.

## 10. Relación con `sn-spectral`

La skill `sn-spectral` calcula el espectro de un medio homogéneo infinito:
autovalores `ν`, autofunciones y la constante

$$
c = \frac{\Sigma_s}{\Sigma_t} + \frac{4\pi\,\nu\Sigma_f}{k\Sigma_t}.
$$

En el medio infinito crítico `c = 1`; eso da `k = 4πνΣf/(Σt−Σs)` en la
convención de esa skill. El solver `NTS_DD_1D` usa la convención estándar
sin `4π`, así que el `k_eff` de una placa finita **no** se obtiene
directamente de `sn-spectral`: hace falta resolver el problema de contorno
con vacío o reflexivas.

## 11. Referencias internas

- `README.md` — referencia del CLI y del formato de configuración.
- `doc/QUICKSTART.md` — cheatsheet.
- `doc/NTS_DOCUMENTATION.md` — documentación de los solvers 2D en C.
- `tests/test_dd_1d_fission.py` — tests de aceptación.
- `solvers/runners/config.py`, `runner.py`, `scheme.py` — configuración,
  motor de transporte y dispatch de esquemas.
- `solvers/runners/NTS_DD_1D.md`, `NTS_STEP_1D.md`, `NTS_SC_1D.md` — fichas por método.
- `skills/nts-pinns-autopilot/SKILL.md` — guía operativa de la skill.
