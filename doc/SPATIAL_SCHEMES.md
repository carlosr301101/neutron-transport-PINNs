# Esquemas de discretización espacial (DD, STEP, SC)

Referencia de los esquemas de celda del solver 1D en Python
(`solvers/runners/NTS_DD_1D.py`).

> **Alcance:** exclusivo del solver 1D. Los programas 2D en C (`NTS_DD`,
> `NTS_LD`, `NTS_STEP`, `NTS_RM_CN`, `NTS_RM_LLN`) conservan su propio
> esquema y no se ven afectados por `SPATIAL_SCHEME`.
>
> Versión en inglés: [SPATIAL_SCHEMES_EN.md](SPATIAL_SCHEMES_EN.md).

## 1. Elementos comunes

La selección cambia **solo el kernel de celda**. Todo lo demás es común:

- fuente isotrópica total `S = ½(Q + ΣsΦ) + S_fisión` (`S_fisión` ya lleva su
  `½`);
- cuadratura angular (`N`, `miu_m`, `omega_m`);
- condiciones de frontera de vacío y reflexivas;
- iteración de fuente, power iteration y criterios de convergencia;
- estimación de `k_eff` y normalización opcional de potencia.

El barrido mantiene los dos bucles (celdas de izquierda a derecha para `μ>0`,
de derecha a izquierda para `μ<0`) y el mismo almacenamiento en interfaces
(`PSI_RIGHT`, `PSI_LEFT`).

## 2. Balance de celda

Todos los esquemas satisfacen, por celda y por ordenada,

$$
\frac{|\mu|}{\Delta x}\left(\psi_{\text{out}}-\psi_{\text{in}}\right)
+ \Sigma_t \bar{\psi} = S .
$$

Lo que difiere es el cierre: cada esquema elige una aproximación distinta
para `ψ̄` y de ella deriva `ψ_out`.

Notación: `a = |μ|/Δx`, `α = ΣtΔx/|μ|`.

## 3. Diamond Difference (`DD`, por defecto)

$$
\psi_{\text{out}} = \frac{(a-\Sigma_t/2)\psi_{\text{in}}+S}{a+\Sigma_t/2},
\qquad
\bar{\psi} = \frac{\psi_{\text{in}}+\psi_{\text{out}}}{2}.
$$

Segundo orden en `Δx`. Es el esquema histórico, así que `"DD"` reproduce
exactamente los resultados anteriores (mismas operaciones en coma flotante).

## 4. Step Difference (`STEP`)

$$
\psi_{\text{out}} = \frac{a\,\psi_{\text{in}}+S}{a+\Sigma_t},
\qquad
\bar{\psi} = \psi_{\text{out}}.
$$

Upwind implícito: la media de celda se toma como el valor de la cara
**aguas abajo**. Eso lo hace incondicionalmente positivo (sin flujos
negativos), a costa de precisión de primer orden.

> La variante explícita (`ψ̄ = ψ_in`) **no** está implementada: es inestable
> en celdas ópticamente gruesas.

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

`θ` es un peso convexo en `[0,1)`: tiende a `0` en celdas finas (SC → DD) y a
`1` en celdas gruesas (la media → convención STEP). Segundo orden en `Δx`.

### Numérica de `θ`

- `α = 0` (sin atenuación) devuelve `θ = 0`.
- `α < 1e-3` usa la serie
  `θ = α/6 − α³/360 + α⁵/15120 + O(α⁷)`. La forma cerrada sufre cancelación
  catastrófica en ese rango: con `α = 1e-6` pierde ~0.16 %, mientras que la
  serie es exacta a precisión de máquina.
- `α ≥ 1e-3` usa `1/tanh(α/2) − 2/α`, que satura sin desbordar (`tanh` llega
  a 1.0 alrededor de `α ≈ 40`).
- Espesor óptico negativo lanza `ValueError`; `α = inf` devuelve `1.0`.
- `θ` se precalcula una vez por corrida como un arreglo `(NTC, N_HALF)`
  (`Config.theta_sc`) y lo reutilizan el barrido y la integración del flujo
  escalar, así que el coste de `tanh` se paga una sola vez.

## 6. Cómo seleccionar el esquema

JSON / `inputs.py`:

```json
{
  "SPATIAL_SCHEME": "SC"
}
```

Valores aceptados: `"DD"`, `"STEP"`, `"SC"` (sin distinguir mayúsculas;
`"step_characteristic"` es un alias). Omitir el campo equivale a `"DD"`. Un
valor inválido lanza `ValueError` al construir la configuración.

El asistente interactivo (`nts-1d-run --manual` y `nts-1d-config`) pregunta,
justo después del orden de cuadratura:

```text
Spatial scheme (DD / STEP / SC) [DD]:
```

`Config.SPATIAL_SCHEME` es la única fuente de verdad: `Config.method` es una
propiedad de solo lectura que lo parsea, de modo que el string que se escribe
en el JSON y el enum que usa el solver no pueden divergir.

## 7. Flujo escalar

El flujo escalar usa las medias de celda del esquema seleccionado:

$$
\phi_i = \sum_{m>0} w_m\left(\bar{\psi}^{+}_{m,i}
+ \bar{\psi}^{-}_{m,i}\right).
$$

`ψ̄` se reconstruye a partir de los dos valores de interfaz después de cada
barrido, así que no se almacenan arreglos de medias. `angular_flux[k, m]`
conserva su significado histórico `ω_m(ψ̄⁺ + ψ̄⁻)`, que es lo que muestra
`nts-1d-plot --kind angular`.

## 8. Resultados de referencia

Placa homogénea de 20 cm, vacío, `σt = 1.0`, `σs0 = 0.9`, `νσf = 0.11`,
`TOL_K = 1e-6`:

| N | DD | STEP | SC |
|---|---|---|---|
| S2 | 1.024641 | 1.014232 | 1.024023 |
| S4 | 1.026509 | 1.017327 | 1.025885 |
| S8 | 1.026676 | 1.017843 | 1.026054 |

Convergencia de malla (S8):

| Celdas | DD | STEP | SC |
|---|---|---|---|
| 25 | 1.026539 | 0.994259 | 1.017809 |
| 50 | 1.026649 | 1.009516 | 1.024237 |
| 100 | 1.026676 | 1.017843 | 1.026054 |
| 200 | 1.026683 | 1.022198 | 1.026526 |

DD y SC convergen a `≈1.026689`; STEP converge al mismo límite pero en primer
orden, así que en mallas prácticas queda ~0.9 % (100 celdas) o ~0.45 %
(200 celdas) por debajo de DD. **Es el comportamiento esperado de la
aproximación de escalón, no un defecto.**

Chequeo independiente del esquema: una placa con fronteras reflexivas en
ambos lados no tiene fuga y `k_eff = νΣf/Σa`. Los tres esquemas devuelven
`0.5999998` para el caso analítico `0.6`.

## 9. Comportamiento numérico y limitaciones

No hay **recorte, restricción de positividad ni corrección artificial** de los
flujos. Cada esquema muestra su comportamiento natural:

| Celda, `α = 50`, `ψ_in = 1`, `S = 0` | `ψ_out` | `ψ̄` |
|---|---|---|
| DD | −0.923 | +0.038 |
| STEP | +0.0196 | +0.0196 |
| SC | 0.0 (a redondeo) | +0.020 |

- DD puede producir flujos angulares negativos en celdas ópticamente gruesas
  o con gradientes fuertes. Refina la malla si ocurre.
- STEP es monótono positivo pero difusivo: sobreestima el flujo alrededor de
  fuentes localizadas.
- SC se mantiene cerca de DD y se comporta mucho mejor que DD en celdas
  gruesas, pero no es "atenuación exacta": su `ψ_out` es una aproximación de
  fuente lineal y no reproduce `ψ_in·e^{−α}` para `α` grande.
- Ningún esquema acelera la convergencia; el número de iteraciones internas
  es similar (SC y DD algo mayor que STEP).
- Las diferencias entre esquemas son diferencias físicas de discretización.
  Solo DD es compatible bit a bit hacia atrás.

## 10. Validación

`tests/test_spatial_schemes.py` cubre:

- balance de celda para los tres esquemas en rejilla aleatoria (residual
  relativo `< 1e-9`);
- consistencia entre `cell_average()` y la media implícita del barrido;
- límites de `θ` (`α = 0`, `inf`, negativo, NaN), continuidad serie/forma
  cerrada, monotonía y rango;
- SC → DD en celdas finas y media SC → convención STEP en celdas gruesas;
- normalización de `|μ|`, rechazo de `|μ| = 0` y de esquemas desconocidos;
- ausencia de positividad artificial (el signo en celda gruesa se reporta, no
  se corrige);
- regresión DD con los resultados congelados previos al refactor;
- medio reflectivo infinito para los tres (`k_eff = 0.6`);
- el benchmark de 20 cm para los tres;
- balance por celda a nivel de solver para los tres;
- fronteras de vacío y reflexivas para los tres.

```bash
uv run nts-test
```

## 11. Referencias internas

- `solvers/runners/NTS_DD_1D.py` — `Method`, kernels, `cell_out`,
  `cell_average`, `Config.theta_sc`.
- `tests/test_spatial_schemes.py` — tests de los esquemas.
- `doc/MULTIPLICATIVE_MEDIA.md` — modos de fisión y `k_eff`.
- `doc/SPATIAL_SCHEMES_EN.md` — versión en inglés.
