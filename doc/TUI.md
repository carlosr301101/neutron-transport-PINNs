# TUI 1D de NTS

Interfaz de terminal para el flujo 1D completo: configuración, corridas,
resultados, gráficas, sweeps y exportación.

> Alcance: solo 1D. Los solvers 2D en C siguen siendo exclusivos de la CLI.
>
> Versión en inglés: [TUI_EN.md](TUI_EN.md).

## Inicio

`uv run nts-tui` es la entrada directa y evita el parser de la CLI. `uv run
nts tui` usa un atajo que también evita importar `cli.commands`.

Los módulos pesados (`pandas`, `matplotlib`, `openpyxl`) se cargan solo cuando
se usan. Results y Plots leen sus archivos al activar la pestaña por primera
vez.


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

- **Geometría y materiales**: barra de geometría coloreada por zona, tabla
  editable de regiones (`cells`, `length`, `zone`, `Q`) y tabla editable de
  zonas (`Sigma_t`, `Sigma_s0`). Agregar o quitar filas con los botones. `Q`
  es la fuente externa por región (`0` = ninguna); se oculta y se fuerza a
  cero en `eigenvalue`.
- **Physics mode**: `MODE` es el primer campo.
  - `fixed_source`: oculta fisión y la tabla de fisión; `NU_SIGF` se guarda
    como cero.
  - `eigenvalue`: muestra tabla de fisión, `TOL_K`, `MAX_OUTER`, `K0` y los
    campos de potencia; `K_EFF` queda oculto.
  - `fixed_k`: muestra tabla de fisión, `K_EFF`, `TOL_K`, `MAX_OUTER` y los
    campos de potencia.
  - `driven`: muestra tabla de fisión y potencia; `K_EFF` queda oculto porque
    el solver usa `k = 1`.
- **Fisión por zona**: tabla editable de `nu*Sigma_f` y `Sigma_f` opcional.
- **Angular**: `N`, `SPATIAL_SCHEME`.
- **Fuente y fronteras**: `Q` va en la tabla de regiones; el resto son
  `reflex_izq`, `reflex_der`, `bound_left`, `bound_right`. Un escalar de
  frontera se expande a `N/2` valores iguales; un vector completo se respeta.
  Ejemplo con `N=8`: `0` pasa a `[0,0,0,0]`, `1` a `[1,1,1,1]` y `[0,1,1,0]`
  se conserva. Las fronteras reflexivas ocultan el flujo entrante
  correspondiente.
- **Convergencia**: `epsilon`, `max_iter`.

Solo los arreglos de frontera usan valores separados por comas. Los campos
numéricos aceptan placeholders (`kk`, `mm`, ...) para expandirlos en Sweep.

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
- `Run selected` muestra el log de la CLI en vivo. `Cancel` termina el proceso,
  espera su salida y escala a `kill` si no responde.
- Al terminar, todas las pestañas se refrescan solas (`refresh_all`). Cerrar la
  TUI cancela cualquier corrida en curso.

Los configs con placeholders sin resolver se rechazan; hay que expandirlos en
Sweep.

## Pestaña Results

La tabla muestra una fila por run. Al seleccionar una fila se ven modo,
esquema, `k_eff`, `k_balance`, iteraciones externas, actualizaciones de flujo,
convergencia y rango del flujo. `Use in Plots` manda el archivo a Plots.

## Pestaña Plots

- Archivo de resultados y selector de run.
- Tipos: scalar, angular, `k_history`.
- Las gráficas angulares siempre dibujan todas las direcciones (una línea por componente).
- Ruta del PNG (vacía usa el siguiente nombre por defecto).
- `Open` abre el PNG con la aplicación por defecto.
- Sección SCS: `datos.json`, eje x (`SCS`, `NU_SIGF`, `k_eff`) y PNG de salida.

## Pestaña Sweep

1. Cargar un config con placeholders.
2. Completar `start`, `end` y `step` para cada placeholder.
3. `Preview` muestra la cantidad de configs y el primero.
4. `Save` escribe una lista JSON o un `.py` (`config_dict_###`).
5. `Run sweep` ejecuta el lote y escribe un único archivo de resultados;
   `Cancel` detiene la corrida en curso.

## Pestaña Export

- `Extract flux`: escribe `datos.json` para los índices de celda indicados.
- `Write Excel`: exporta el archivo de resultados seleccionado.
- `Write SCS plot`: grafica `datos.json` contra `SCS`, `NU_SIGF` o `k_eff`.

## Tests

```bash
uv run nts-test -p "test_tui_*.py" -v
```
