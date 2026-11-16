# TUI 1D de NTS

Interfaz de terminal para el flujo 1D completo: configuración, corridas,
resultados, gráficas, sweeps y exportación.

> Alcance: solo 1D. Los solvers 2D en C siguen siendo exclusivos de la CLI.
>
> Versión en inglés: [TUI_EN.md](TUI_EN.md).

## Inicio

```bash
uv run nts tui
# equivalente
uv run nts-tui
```

Preview de imagen inline opcional:

```bash
uv sync --extra images
```

El preview usa el protocolo de imagen de la terminal cuando está disponible
(Kitty, WezTerm, iTerm2, sixel). Si no, se muestra la ruta del PNG y el botón
`Open` abre el archivo con la aplicación por defecto.

## Pestañas

| Pestaña | Función |
|---|---|
| Dashboard | Versión, cantidad de configs, resultados y último resultado |
| Config | Wizard 1D completo: geometría, materiales, angular, fisión, fuente, fronteras y convergencia |
| Run | Selección de configs, esquema opcional, JSON de salida, Excel, log en vivo y cancelar |
| Results | Tabla de runs con `k_eff`, `k_balance`, iteraciones y convergencia |
| Plots | Gráficas scalar, angular, `k_history` y SCS con preview inline opcional |
| Sweep | Rangos de placeholders, preview, guardar JSON/Python y corrida por lote |
| Export | `datos.json`, Excel y gráfica SCS |

## Pestaña Config

El formulario refleja `Config.manual_input` y `nts-1d-config`:

- Geometría: `num_regions`, `num_zones`, `NC`, `HR`, `IZL`.
- Materiales: `SCT`, `SCS` por zona.
- Angular: `N`, `SPATIAL_SCHEME`.
- Fisión: `NU_SIGF`, `SIGMA_F`, `MODE`, `K_EFF`, `TOL_K`, `MAX_OUTER`, `K0`,
  `POWER_KW`, `E_F_MEV`, `NU`, `AREA_CM2`.
- Fuente y fronteras: `Q`, `reflex_izq`, `reflex_der`, `bound_left`,
  `bound_right`.
- Convergencia: `epsilon`, `max_iter`.

Los campos de lista aceptan valores separados por comas. Los campos numéricos
aceptan placeholders (`kk`, `mm`, ...) para expandirlos en Sweep.

Acciones:

- `Validate`: usa la misma validación `Config` que la CLI.
- `Save`: escribe `outputs/inputs/config_1d_###.json` o la ruta del formulario.
- `Load`: lee un config existente del desplegable.
- `New`: reinicia el formulario con los valores por defecto.

## Pestaña Run

- Seleccionar uno o varios configs.
- Override opcional de esquema (`DD`, `STEP`, `SC`).
- Ruta del JSON de salida (vacía usa el siguiente `output_1d_###.json`).
- Switch de Excel: escribe el libro junto al JSON.
- `Run selected` muestra el log de la CLI en vivo. `Cancel` termina el proceso.

Los configs con placeholders sin resolver se rechazan; hay que expandirlos en
Sweep.

## Pestaña Results

La tabla muestra una fila por run. Al seleccionar una fila se ven modo,
esquema, `k_eff`, `k_balance`, iteraciones externas, actualizaciones de flujo,
convergencia y rango del flujo. `Use in Plots` manda el archivo a Plots.

## Pestaña Plots

- Archivo de resultados y selector de run.
- Tipos: scalar, angular, `k_history`.
- Direcciones para angular (`0, 1, ...`; vacío usa todas).
- Ruta del PNG (vacía usa el siguiente nombre por defecto).
- `Open` abre el PNG con la aplicación por defecto.
- Sección SCS: `datos.json`, eje x (`SCS`, `NU_SIGF`, `k_eff`) y PNG de salida.

## Pestaña Sweep

1. Cargar un config con placeholders.
2. Completar `start`, `end` y `step` para cada placeholder.
3. `Preview` muestra la cantidad de configs y el primero.
4. `Save` escribe una lista JSON o un `.py` (`config_dict_###`).
5. `Run` ejecuta el lote y escribe un único archivo de resultados.

## Pestaña Export

- `Extract flux`: escribe `datos.json` para los índices de celda indicados.
- `Write Excel`: exporta el archivo de resultados seleccionado.
- `Write SCS plot`: grafica `datos.json` contra `SCS`, `NU_SIGF` o `k_eff`.

## Tests

```bash
uv run nts-test -p "test_tui_*.py" -v
```
