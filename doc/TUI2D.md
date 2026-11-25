# TUI 2D de NTS

Interfaz de terminal para el flujo 2D completo: configuración con un mapa
proporcional del dominio, corridas con los cinco solvers C, resultados y
mapas de calor de `MFLUX`.

> Alcance: solo 2D. El flujo 1D conserva su propia interfaz en [TUI.md](TUI.md).
>
> Versión en inglés: [TUI2D_EN.md](TUI2D_EN.md).

## Inicio

```bash
uv run nts tui --dim 2
# equivalente
uv run nts-tui-2d
```

`nts tui` sin `--dim` sigue abriendo la TUI 1D, así que nada cambia para quien
ya la usa. `nts tui --dim 2` usa un atajo en `cli/main.py` que evita el parser
de la CLI.

Antes de correr, `nts status` debe mostrar los cinco binarios:

```text
Solvers:
  OK NTS_DD
  OK NTS_LD
  OK NTS_RM_CN
  OK NTS_RM_LLN
  OK NTS_STEP
```

Si faltan, compílalos con `make -C solvers` (Linux) o
`solvers/build_windows.ps1` (Windows).

Vista previa de imágenes en línea (opcional):

```bash
uv sync --extra images
```

## Pestañas

| Pestaña | Contenido |
|---|---|
| Dashboard | Versión, número de configs/resultados y último resultado |
| Config | Zonas, regiones X/Y, `ZMAP`, `QMAP`, fronteras, `N`, `TOL`, solver y preview de `input.txt` |
| Run | Selección de configs, solver y workers; preview, log en vivo y cancelación |
| Results | `STATUS`, `ITER`, `CPU`, forma de la malla y flujo medio de cada resultado |
| Plots | Heatmap de `MFLUX` con ejes en cm |

## Pestaña Config

El formulario replica `nts-2d-config` y produce el JSON que consumen
`nts validate` / `nts generate`.

### Mapa proporcional del dominio

En la parte superior se dibuja el dominio físico:

- El ancho y el alto siguen la suma de las longitudes de las regiones X e Y
  en cm.
- Un carácter de terminal es aproximadamente el doble de alto que de ancho,
  así que el dibujo usa `filas = columnas * (Ly / Lx) * 0.5`. Un dominio de
  20 x 10 cm se dibuja el doble de ancho que de alto; uno de 10 x 20 cm se
  dibuja el doble de alto que de ancho.
- Cada región se rellena con el color de su zona según `ZMAP`.
- Las líneas negras `│`, `─` y `┼` marcan los bordes entre regiones.
- La leyenda muestra longitud total, número de regiones y celdas, la relación
  de aspecto dibujada, la paleta de zonas y las fronteras como
  `BC: L=Reflective · B=Vacuum · R=Incoming(2) · T=Vacuum`.

El mapa se actualiza con cada edición de las tablas de regiones, `ZMAP` o la
tabla de fronteras.

### Tablas y campos

- **Fronteras** (justo debajo del mapa): una fila por lado en el orden
  canónico `left, bottom, right, top`:
  - `Reflective` → `-1.0`
  - `Vacuum` → `0.0`
  - `Incoming flux` → el valor positivo escrito
- **Zonas**: `Name` opcional, `Sigma_t`, `Sigma_s`. `Sigma_s` debe ser menor
  que `Sigma_t`. Los nombres se guardan como `ZONE_NAMES`; hay que llenarlos
  todos o dejar todos en blanco.
- **Regiones X** y **Regiones Y**: `Length [cm]` y `Cells` por región. El
  número de filas es `NR_X` / `NR_Y`; `Cells` cuenta celdas y debe ser `>= 3`.
  Las filas X van de izquierda a derecha; las Y de abajo hacia arriba.
- **ZMAP**: un entero por región, las filas son Y (abajo → arriba) y las
  columnas son X (izquierda → derecha), valores `1..NZ`. La matriz se redimensiona
  automáticamente al cambiar las regiones.
- **QMAP**: un valor de fuente por región, `>= 0`.
- **Ajustes del solver**: `N` (par, 2–18), `TOL` (rango Python `1e-7 … 1e-2`)
  y el solver preferido (`NTS_DD` por defecto). El solver se guarda como
  `_solver`, la misma pista que escribe `nts-2d-config`; no cambia la física
  del JSON.
- **Preview de input.txt**: el texto exacto de 11 parámetros que recibe el C.

### Botones

| Botón | Acción |
|---|---|
| Load | Carga el `config_2d_*.json` seleccionado |
| New | Vuelve a la configuración por defecto y elige la siguiente ruta libre |
| Validate | Validación Pydantic; la barra de estado muestra los primeros errores |
| Save | Valida y escribe el JSON (con `_solver`) |

La lista `Load config...` se recarga cada vez que se abre la pestaña Config,
así que los JSON guardados desde la CLI u otra sesión aparecen solos.

## Pestaña Run

1. `Refresh` recarga `outputs/inputs/config_2d_*.json`. La lista también se
   refresca al abrir la pestaña y conserva la selección actual.
2. Selecciona una o varias configuraciones (espacio alterna la selección).
3. Elige solver y número de workers (1–4).
4. El campo **Output** viene relleno con la siguiente ruta libre
   (`outputs/results/output_NNN.json`) y es editable: otra carpeta y/o nombre,
   o vacío para numeración automática.
   - Una configuración: se usa la ruta tal cual.
   - Varias configuraciones: el nombre actúa de prefijo
     (`caso_001.json`, `caso_002.json`, …).
   - Un archivo existente nunca se sobrescribe; se añade `_001` y la ruta real
     aparece en `Last output:`.
5. El preview muestra el `input.txt` de la primera configuración.
6. `Run selected` genera `input_NNN.txt`, ejecuta el binario y escribe el
   archivo de salida elegido.
7. `Cancel` termina los procesos en curso.

El log muestra cada inicio y fin con `STATUS`, `ITER`, `CPU` y la ruta exacta
de salida, por ejemplo:

```text
[config_2d_001.json] started input_010.txt -> outputs/results/output_010.json
OK config_2d_001.json: STATUS=0 ITER=19 CPU=0.000584
   -> outputs/results/output_010.json
Output: outputs/results/output_010.json
```

`Last output: ...` queda visible bajo la barra de estado y `Plot latest` abre
Plots con ese archivo seleccionado. `Results` abre Results con él
seleccionado. Los resultados también aparecen solos en Results/Plots al
terminar la corrida.

Con un nombre personalizado, el input asociado se escribe como
`outputs/inputs/<stem>.txt`; la pestaña Plots lo encuentra automáticamente.

## Pestaña Results

Una fila con `STATUS`, `ITER`, `CPU [s]`, `Grid` y `Mean flux`. Al seleccionar
una fila se ven la ruta, la forma de la malla y el flujo medio, mínimo y
máximo. `Use in Plots` cambia a la pestaña Plots con ese archivo exacto
seleccionado.

Los archivos del solver 1D (`output_1d_*.json`) se ignoran porque usan otro
esquema.

## Pestaña Plots

- La pestaña muestra el directorio de resultados (`outputs/results/`) y los
  archivos disponibles. Un resultado recién creado se selecciona solo; la
  lista se refresca cada vez que se abre la pestaña Plots.
- Selector de resultado y campo **Result path** para archivos fuera del
  directorio de resultados: escribe la ruta y pulsa `Load path`.
- Geometría opcional. El `input_NNN.txt` que corresponde se rellena solo; de
  ahí salen los ejes en cm.
- Ruta del PNG (por defecto, el siguiente `outputs/results/plots/mflux_2d.png`).
- `Generate` ejecuta matplotlib en un hilo de trabajo, sin congelar la UI.
- El heatmap usa `origin="lower"`, ejes `x [cm]` / `y [cm]` cuando hay
  geometría y una barra de color. Sin geometría usa índices de celda.
- `Open` abre el PNG con la aplicación por defecto.
- Con `textual-image` y un terminal compatible, el PNG se muestra en línea.

## Archivos

```text
outputs/inputs/config_2d_###.json    configuraciones editables
outputs/inputs/input_###.txt         entrada exacta del solver
outputs/results/output_###.json      JSON del solver (STATUS, ITER, CPU, MFLUX, ...)
outputs/results/plots/mflux_2d.png   heatmaps
outputs/logs/tui2d.log               diagnóstico
```

## Diferencias con la TUI 1D

- La TUI 1D no se modifica; `nts tui` sigue abriéndola.
- La TUI 2D no tiene pestañas de placeholders, Excel ni `datos.json`: eso
  pertenece al flujo 1D.
- `MFLOW`, `XFLOW` y `YFLOW` no se muestran; el JSON los conserva.
- El mapa del dominio es 2D y proporcional en lugar de la barra 1D.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `Solver binary not found` | `make -C solvers` (Linux) o `solvers/build_windows.ps1` |
| `STATUS=2` en una corrida | La entrada viola el contrato; revisa `BC` y `N` |
| El plot muestra índices de celda | Indica el `input_###.txt` correspondiente en geometría |
| El mapa sale deformado | Alguna longitud de región es cero o negativa |
| `Sigma_s must be lower than Sigma_t` | Corrige la tabla de zonas |
| No hay preview en línea | `uv sync --extra images` y un terminal compatible |

## Tests

```bash
uv run python -m cli.run_tests -p "test_tui2d.py" -v
```
