# Integración de los solvers 2D en CLI y TUI

Estado: **en implementación**. Fases 0–4 completadas; fases 5–7 pendientes.
El contrato de entrada/salida vive en `doc/2D_SOLVERS_CONTRACT.md`.

Este documento describe la implementación de los
cinco solvers C (`NTS_DD`, `NTS_LD`, `NTS_STEP`, `NTS_RM_CN`, `NTS_RM_LLN`)
en el flujo completo de NTS.

Rama de trabajo:

```text
feat/2d-integration
```

## Objetivo

Integrar los solvers 2D de C en:

- configuración y validación de geometrías 2D;
- wizard de consola;
- CLI;
- TUI 2D;
- ejecución de los binarios;
- resultados y heatmaps;
- tests Linux/Windows;
- distribución dentro del wheel principal;
- documentación y skill.

## Decisiones de diseño

```text
BC:            [left, bottom, right, top]
               -1.0 reflectivo | 0.0 vacío | >0 flujo entrante
Malla:         nodes >= 3
TUI:           paquete separado tui2d
Distribución:  binarios dentro del wheel principal
               wheels Linux y Windows
```

No se crea un paquete `nts-solvers` ni un extra `[solvers]`. El wheel principal
pasa a ser específico de plataforma.

## Estado actual y bloqueos

### 1. Orden y semántica de BC

El código C usa:

```text
BC[0] = LEFT
BC[1] = BOTTOM
BC[2] = RIGHT
BC[3] = TOP

-1.0  reflectivo / simetría
 0.0  vacío
 >0   flujo entrante especificado
```

El código Python actual usa `[left, right, bottom, top]` y solo acepta `0.0` o
`1.0`. Además, `1.0` en el C significa flujo entrante, no reflectivo.

**Decisión:** el contrato canónico es el del C. Los ejemplos y templates usan
`-1.0` para reflectivo. `1.0` queda reservado para flujo entrante.

### 2. Portabilidad de los C

Los cinco archivos incluyen `<unistd.h>`. `NTS_DD` y `NTS_STEP` llaman a
`sleep(1)`. El cálculo de `CPU` resta un segundo y puede producir valores
negativos:

```c
*cpu_time = (long double)(end_t - start_t) / CLOCKS_PER_SEC - 1.0;
```

### 3. Falta de tests 2D

No hay pruebas de `SimulationConfig`, `InputBuilder`, CLI 2D, TUI 2D ni de los
binarios C.

### 4. Ejemplos JSON inválidos

Tres de los cinco ejemplos de `solvers/doc_solvers/` no parsean:

```text
NTS_LD_EXAMPLE_INPUT.json
NTS_RM_CN_EXAMPLE_INPUT.json
NTS_STEP_EXAMPLE_INPUT.json
```

## Fase 0: rama, limpieza y contrato

### Tareas

- Restaurar o guardar los cambios locales:
  ```text
  Config.log
  outputs/inputs/config_1d_001.json
  ```
- Crear la rama:
  ```bash
  git switch -c feat/2D-solvers-integrations
  ```
- Crear `doc/2D_SOLVERS_CONTRACT.md` con:
  - orden y semántica de `BC`;
  - `N` par entre 2 y 18;
  - `nodes >= 3`;
  - `ZMAP` y `QMAP` de `NR_Y × NR_X`;
  - formato del `input.txt` de 11 líneas;
  - campos de salida `STATUS`, `ITER`, `CPU`, `MFLUX`, `MFLOW`, `XFLOW`,
    `YFLOW`;
  - responsabilidades de cada solver.
- Corregir los tres JSON inválidos.

### Archivos

```text
doc/2D_SOLVERS_CONTRACT.md
solvers/doc_solvers/NTS_LD_EXAMPLE_INPUT.json
solvers/doc_solvers/NTS_RM_CN_EXAMPLE_INPUT.json
solvers/doc_solvers/NTS_STEP_EXAMPLE_INPUT.json
```

### Criterio de aceptación

```text
json.load funciona en los cinco ejemplos
contrato aprobado
rama creada
```

## Fase 1: núcleo 2D

### `core/config.py`

- Orden de `BC`: `[left, bottom, right, top]`.
- Valores permitidos: `-1.0`, `0.0` y `> 0`.
- Rechazar valores entre `-1.0` y `0.0`.
- `DomainRegion.nodes: ge=3`.
- `N`: par, `2 <= N <= 18`.
- `ZMAP`: `NR_Y × NR_X`, valores `1..NZ`.
- `QMAP`: `NR_Y × NR_X`, valores `>= 0`.
- `XDOM` y `YDOM`: longitudes `NR_X` y `NR_Y`.
- Lectura y escritura JSON en UTF-8.

### `core/validator.py`

- Resumen con etiquetas:
  ```text
  Left, Bottom, Right, Top
  ```
- Mostrar el tipo de BC:
  ```text
  Left=Vacuum, Bottom=Reflective, ...
  ```

### `core/input_builder.py`

- Escribir `BC` en el orden canónico.
- UTF-8.
- Sin conversiones implícitas de `1.0`.

### Templates y ejemplos

- `templates/base_input.json`: comentarios y semántica correctos.
- `example_config.json`: consistente con el contrato.
- `nodes >= 3`.

### Tests

```text
tests/test_2d_config.py
  - BC válidas e inválidas
  - orden de BC
  - N par y rango
  - nodes < 3 falla
  - ZMAP/QMAP dimensiones y rangos
  - round-trip JSON UTF-8

tests/test_2d_input_builder.py
  - golden de 11 líneas para los cinco ejemplos
  - BC en el orden correcto
  - N y TOL
```

### Criterio de aceptación

```bash
nts validate example_config.json
nts generate example_config.json
```

El `input.txt` coincide con el golden y el C lo acepta.

## Fase 2: CLI y wizard 2D

### Wizard

Nuevo módulo:

```text
utils/generate_2d_config.py
entry point: nts-2d-config
```

Preguntas:

```text
N
NZ
σt, σs por zona
NR_X
length, nodes por región X
NR_Y
length, nodes por región Y
ZMAP fila por fila
QMAP fila por fila
BC left/bottom/right/top
TOL
solver preferido
```

Comportamiento:

- Reintentar en errores de matriz.
- Aceptar filas `1 2` o `1,2`.
- Mostrar resumen antes de guardar.
- Guardar JSON validado.
- `-o/--output`.

### CLI

- `nts generate`: 2D con preview.
- `nts validate`: resumen 2D.
- `nts run`: selección de solver y `.exe` en Windows.
- `nts show`: `STATUS`, `ITER`, `CPU`, dimensiones de `MFLUX`.
- `nts plot`: ejes físicos en cm a partir de `XDOM/YDOM`.
- `nts run --dry-run`: mostrar input y comando sin ejecutar.

### Archivos

```text
utils/generate_2d_config.py
cli/commands.py
cli/main.py
pyproject.toml
```

### Tests

```text
tests/test_2d_cli.py
  - wizard con respuestas simuladas
  - generate/validate/run/show/plot
  - NTS_HOME temporal
  - error de BC
```

### Criterio de aceptación

```bash
nts-2d-config -o caso.json
nts validate caso.json
nts generate caso.json
nts run -s NTS_DD -i outputs/inputs/input_001.txt
nts show outputs/results/output_001.json
nts plot -r outputs/results/output_001.json
```

## Fase 3: C solvers y portabilidad

### Cambios en C

- Quitar `<unistd.h>` de los cinco archivos.
- Quitar `sleep(1)` de los cinco (lo tenían DD, LD, STEP, RM_CN y RM_LLN).
- Corregir el tiempo:
  ```c
  *cpu_time = (long double)(end_t - start_t) / CLOCKS_PER_SEC;
  ```
- Activar el alias de MinGW solo en Windows:
  ```c
  #ifdef _WIN32
  #define printf __mingw_printf
  #endif
  ```
  Así Linux compila sin `-D__mingw_printf=printf` ni editar el fuente.
- Mantener los códigos de estado:
  ```text
  0 éxito
  1 argumentos
  2 lectura
  3 memoria
  ```

### Build

```text
solvers/Makefile           Linux y MSYS2 (detecta Windows para .exe y -static)
solvers/build_windows.ps1  MSYS2/MinGW-w64
```

Linux:

```bash
make -C solvers
# equivale a:
gcc -O2 -o solvers/runners/NTS_DD solvers/runners/NTS_DD.c -lm
```

Windows:

```powershell
pwsh -File solvers/build_windows.ps1
# gcc -O2 -static -o solvers/runners/NTS_DD.exe solvers/runners/NTS_DD.c -lm
```

`-static` evita depender de DLLs de MinGW.

### Runtime

- `utils/paths.py`:
  - En Linux busca `NTS_DD`; en Windows solo `NTS_DD.exe` (un binario Linux
    sin extensión no es ejecutable en Windows).
  - `verify_solver_binaries()` usa la misma lógica.
- `execution/runner.py`:
  - UTF-8 al abrir el output.
  - Error claro si falta el binario.

### CI

- Linux: `make -C solvers` antes de los tests.
- Windows: MSYS2/UCRT64 + `build_windows.ps1` antes de los tests.

### Criterio de aceptación

```text
los cinco binarios compilan en Linux
los cinco .exe compilan en Windows
STATUS=0, ITER>0, MFLUX con forma correcta
CPU >= 0
```

## Fase 4: TUI 2D

Paquete separado:

```text
tui2d/
├── app.py
├── screens/
│   ├── dashboard.py
│   ├── config.py
│   ├── run.py
│   ├── results.py
│   └── plots.py
├── services/
│   ├── config_store.py
│   ├── runner.py
│   └── plots.py
└── widgets/
    ├── matrix_editor.py
    ├── zone_table.py
    ├── region_table.py
    └── bc_table.py
```

Entradas:

```bash
nts tui --dim 2
nts-tui-2d
```

### Config

- `N`, `TOL`.
- Selector de solver.
- Mapa 2D proporcional del dominio (ancho/alto según `XDOM`/`YDOM`, color por
  `ZMAP`, líneas de borde de región, ejes y BC en la leyenda).
- Tabla de zonas (`σt`, `σs`).
- Tabla X (`length`, `nodes`).
- Tabla Y (`length`, `nodes`).
- Editor `ZMAP` (`NR_Y × NR_X`).
- Editor `QMAP` (`NR_Y × NR_X`).
- Tabla BC:

```text
Side       Type         Value
Left       Vacuum       0.0
Bottom     Reflective  -1.0
Right      Vacuum       0.0
Top        Incoming     1.0
```

- Validación inline.
- Preview del input de 11 líneas.

### Run

- Solver.
- Workers.
- Preview.
- Ejecutar/cancelar.
- Log en vivo.
- Output JSON.

### Results

- `STATUS`, `ITER`, `CPU`.
- Dimensiones de `MFLUX`.
- Abrir JSON.
- Preview del heatmap.

### Plots

- Heatmap con ejes `x [cm]` e `y [cm]`.
- `origin="lower"`.
- Colorbar.
- Exportar PNG.

### Tests

```text
tests/test_tui2d.py
  - montar tabs
  - editar ZMAP/QMAP
  - BC correctas
  - validación
  - guardar/cargar JSON
  - run con servicio mock
  - results y plot
```

### Criterio de aceptación

Crear un caso 2D desde la TUI, validarlo, correr `NTS_DD` y ver el heatmap.

## Fase 5: distribución en el wheel principal

### Estrategia

El wheel principal pasa a ser específico de plataforma:

```text
neutron_transport_pinns-3.11.0-py3-none-manylinux_2_28_x86_64.whl
neutron_transport_pinns-3.11.0-py3-none-win_amd64.whl
```

Cada wheel incluye solo los binarios de su plataforma.

### Contenido Linux

```text
solvers/runners/NTS_DD
solvers/runners/NTS_LD
solvers/runners/NTS_STEP
solvers/runners/NTS_RM_CN
solvers/runners/NTS_RM_LLN
```

### Contenido Windows

```text
solvers/runners/NTS_DD.exe
solvers/runners/NTS_LD.exe
solvers/runners/NTS_STEP.exe
solvers/runners/NTS_RM_CN.exe
solvers/runners/NTS_RM_LLN.exe
```

### `setup.py`

Package data dinámico según la plataforma:

```python
binaries = (
    ["NTS_DD.exe", "NTS_LD.exe", "NTS_STEP.exe",
     "NTS_RM_CN.exe", "NTS_RM_LLN.exe"]
    if os.name == "nt"
    else ["NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN"]
)
```

Y un `bdist_wheel` que fuerce el tag de plataforma:

```python
class bdist_wheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        plat = os.environ.get("NTS_WHEEL_PLATFORM", self.plat_name)
        return "py3", "none", plat
```

### Linux

- Compilar dentro de un contenedor `manylinux_2_28`.
- No publicar el `linux_x86_64` del runner directamente.
- Verificar con `auditwheel show` si aplica.

### Windows

- MSYS2/MinGW.
- Enlazado estático (`-static`).
- Wheel `win_amd64`.

### Instalación

```bash
pip install neutron-transport-pinns
nts status
```

Debe mostrar:

```text
OK NTS_DD
OK NTS_LD
OK NTS_STEP
OK NTS_RM_CN
OK NTS_RM_LLN
```

`NTS_SOLVERS_DIR` sigue como override para macOS, otras arquitecturas o builds
locales.

### Sdist

El sdist incluye las fuentes C, pero no los binarios. En plataformas sin wheel
hay que compilar y usar `NTS_SOLVERS_DIR`.

### Release workflow

```text
tag vX.Y.Z
  ├─ build-linux-wheel
  ├─ build-windows-wheel
  ├─ build-sdist
  ├─ twine check
  └─ publish
```

Un solo proyecto PyPI y una sola configuración de trusted publishing.

### Criterio de aceptación

Instalación limpia en Linux y Windows:

```bash
python -m venv /tmp/nts
pip install dist/neutron_transport_pinns-*.whl
nts status
nts run -s NTS_DD -i ...
```

## Fase 6: tests 2D y CI

### Tests

```text
tests/test_2d_config.py
tests/test_2d_input_builder.py
tests/test_2d_cli.py
tests/test_2d_solvers.py
tests/test_tui2d.py
```

### `test_2d_solvers.py`

Para cada solver:

- localizar o compilar el binario;
- correr un caso 2×2, N=4, 20×20 cm;
- verificar:
  - `STATUS == 0`;
  - `ITER > 0`;
  - `CPU >= 0`;
  - `MFLUX` es matriz rectangular;
  - `len(MFLUX) == total nodos Y`;
  - `len(MFLUX[0]) == total nodos X`;
  - flujo positivo en un caso uniforme;
  - simetría en un caso uniforme.

### Test de orden de BC

Dos casos:

```text
BC = [-1, 0, 0, 0]   reflectivo izquierdo
BC = [0, -1, 0, 0]   reflectivo inferior
```

La simetría debe aparecer en el eje correcto. Esto detecta inversiones del
orden de `BC`.

### CI

Matriz:

```text
ubuntu-latest  -> gcc + wheel manylinux + tests
windows-latest -> MSYS2 + wheel win_amd64 + tests
```

Pasos:

1. `uv sync --frozen --extra images`
2. compilar binarios
3. `uv run python -m cli.run_tests`
4. smoke tests C
5. construir wheel
6. instalar wheel en venv limpia
7. `nts status` + corrida 2D
8. `twine check`

### Criterio de aceptación

CI verde en Linux y Windows con binarios compilados.

## Fase 7: documentación y skill

### Documentación

- `README.md`:
  - el wheel incluye los solvers 2D;
  - orden y semántica de `BC`;
  - flujo CLI 2D;
  - TUI 2D.
- `doc/NTS_DOCUMENTATION.md`.
- `doc/QUICKSTART.md`.
- `doc/TUI.md` y `doc/TUI_EN.md`.
- `doc/installing.md` y `doc/INSTALLING_EN.md`.
- `doc/PACKAGING.md` y `doc/PACKAGING_EN.md`.
- `doc/RELEASING.md` y `doc/RELEASING_EN.md`.
- `solvers/doc_solvers/*.md`.

### Skill

`skills/nts-pinns-autopilot/SKILL.md`:

- flujo 2D;
- `nts-2d-config`;
- `nts run -s ...`;
- TUI 2D;
- semántica de BC;
- wheels Linux/Windows;
- solución de problemas.

Actualizar `skills-lock.json`.

### Changelog

Entrada de versión menor, por ejemplo:

```text
3.11.0

Added
- 2D solvers in the main wheel
- nts-2d-config
- tui2d
- platform-specific wheels
```

## Estructura final

```text
cli/
  commands.py
  main.py
core/
  config.py
  input_builder.py
  validator.py
execution/
  runner.py
  parallel.py
utils/
  generate_2d_config.py
  paths.py
tui2d/
  app.py
  screens/
  services/
  widgets/
tests/
  test_2d_config.py
  test_2d_input_builder.py
  test_2d_cli.py
  test_2d_solvers.py
  test_tui2d.py
```

## Secuencia de PRs

```text
PR 1  Fase 0 + 1   contrato, BC, Pydantic, InputBuilder, golden tests
PR 2  Fase 2       wizard y CLI 2D
PR 3  Fase 3       C Linux/Windows, Makefile, CI de compilación
PR 4  Fase 4       tui2d
PR 5  Fase 5 + 6   wheel platform-specific, release, tests 2D
PR 6  Fase 7       docs, skill, changelog
```

## Riesgos

- **BC `1.0`**: cambia de reflectivo a flujo entrante. Actualizar ejemplos y
  documentar la migración.
- **Wheel Linux**: construir en un contenedor manylinux, no en el runner sin
  contenedor.
- **Windows**: usar `-static` para evitar DLLs de MinGW.
- **CPU**: el cambio en C altera el valor reportado. Los tests deben validar
  `CPU >= 0`, no un valor exacto.
- **TUI 2D**: es la fase más grande. Mantenerla separada de la TUI 1D.
- **Sin tests 2D actuales**: cada fase debe cerrar con sus tests antes de
  avanzar.

## Progreso

```text
[x] Fase 0  contrato + JSON de ejemplo válidos
[x] Fase 1  núcleo 2D (BC, Pydantic, InputBuilder, golden tests)
[x] Fase 2  wizard nts-2d-config + CLI 2D
[x] Fase 3  C portables (Linux/Windows), CPU >= 0, Makefile, CI de compilación
[x] Fase 4  tui2d (config con mapa 2D proporcional, run, results, plots)
[ ] Fase 5  wheel platform-specific
[~] Fase 6  tests de solvers y TUI hechos; CI/wheel pendientes
[ ] Fase 7  documentación y skill
```

## Continuación

```bash
git switch feat/2d-integration
```

Después, Fase 5 (wheels específicos de plataforma).
