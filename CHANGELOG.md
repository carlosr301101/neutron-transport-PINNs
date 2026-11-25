# Changelog

Registro de todos los cambios notables en el proyecto NTS Automation System.

## [Unreleased] - 4.0.0

### Breaking changes
- `BC` usa el orden canónico `[left, bottom, right, top]`: `-1.0` reflectivo,
  `0.0` vacío y `> 0` flujo entrante. `1.0` ya **no** significa reflectivo.
- `nodes` debe ser `>= 3` y `N` es par entre 2 y 18.
- El wheel deja de ser `py3-none-any`: ahora es específico de plataforma porque
  incluye los binarios 2D.

### Added
- Solvers C 2D portables: sin `unistd.h`, sin `sleep(1)` y `CPU` real.
- `solvers/Makefile` y `solvers/build_windows.ps1` (MSYS2, `-static`).
- `nts-2d-config`, `core/input_reader`, `nts run --dry-run`, `nts plot -i` y
  resumen de malla en `nts show`.
- TUI 2D (`tui2d`): `nts tui --dim 2` y `nts-tui-2d`, con mapa 2D proporcional,
  editores `ZMAP`/`QMAP`, tabla BC, salida elegible, resultados y heatmaps.
- Wheels Linux `manylinux_2_28_x86_64` y Windows `win_amd64` con los cinco
  binarios; sdist con fuentes C y script de build; plantilla incluida en el
  paquete.
- Tests 2D de configuración, input, CLI, solvers, TUI e idioma.
- CI compila los solvers y prueba cada wheel instalado en una venv limpia.

### Changed
- `nts tui` sigue abriendo la TUI 1D; ambas TUI están en inglés.
- Los selectores de Config/Run/Results/Plots se refrescan al abrir la pestaña.
- El campo `Output` de la TUI 2D permite elegir carpeta y nombre, sin
  sobrescribir archivos existentes.

### Fixed
- Binarios `NTS_LD`, `NTS_RM_CN` y `NTS_RM_LLN` desactualizados que rechazaban
  el input canónico.
- `CPU` negativo y el retardo artificial de un segundo por corrida.
- Huecos de layout en `ZMAP`/`QMAP` y sección de fronteras recortada en la TUI 2D.

## [3.10.0] - 2026-11-20 - Zonas nombradas y gráficas por región

### Added
- `ZONE_NAMES` in the 1D config and a `Name` column in the TUI material-zone
  table.
- `nts-1d-plot --zone-names` to label zones from the CLI.
- Flujo guiado en la skill para crear un problema de transporte 1D nuevo.

### Changed
- Scalar and angular plots shade each region, draw dashed interfaces and
  label `R1..Rn` with the zone name.
- La TUI inicia una configuración nueva con 10 celdas en la región 1.
- El workflow de release ejecuta CI en Ubuntu y Windows y solo publica en PyPI
  si ambos pasan.
- Bump de versión a 3.10.0.

## [3.9.5] - 2026-11-18 - Consola Windows compatible

### Fixed
- `Validate` en la TUI ya no bloquea la interfaz: la validación corre en un
  worker y el botón muestra `Validating...` hasta terminar. El import del
  solver (numpy/pandas) se precalienta en segundo plano al abrir Config, así
  que la primera validación es casi instantánea.
- La CLI ya no falla con `UnicodeEncodeError` en PowerShell ni en consolas
  con code page heredada (`cp1252`/`cp850`).
- Los símbolos `✓`, `✗` y `•` se imprimen como `OK`, `X` y `-` en Windows.
- El spinner y las barras de progreso usan ASCII cuando la consola no es UTF-8.

### Added
- `NTS_UNICODE=1` fuerza los glifos Unicode y `NTS_ASCII=1` fuerza ASCII.
- CI en Windows con una prueba de regresión en `cp1252`.

### Changed
- Bump de versión a 3.9.5.

## [3.9.4] - 2026-11-18 - Versión de release

### Changed
- Bump de versión a 3.9.4 para publicación en PyPI.
- Sin cambios funcionales respecto a 3.9.3.

## [3.9.3] - 2026-11-18 - Versión de release

### Changed
- Bump de versión a 3.9.3 para corregir el tag de release.
- Sin cambios funcionales respecto a 3.9.2.

## [3.9.2] - 2026-11-17 - Panel Placeholders

### Changed
- La pestaña **Sweep** pasa a llamarse **Placeholders** y el panel
  "Placeholder ranges".
- Cada placeholder usa un único rango `inicio:fin:paso` (por ejemplo
  `MM [10:20:1]`) en lugar de tres campos separados; los corchetes y los
  espacios son opcionales.
- `Preview` muestra el resumen por rango
  (`MM: 10 -> 20 (step 1) = 11 value(s)`), la cantidad de configs y la primera.
- Botón `Refresh` para recargar la lista de configs.
- Ids internos renombrados: `tab-placeholders` y `ph-*`; el módulo es
  `tui/screens/placeholders.py`.

### Added
- `parse_range()` y `range_values()` en `tui/services/sweeps.py`, con
  validación de formato, paso > 0 y fin >= inicio.

## [3.9.1] - 2026-11-17 - Rendimiento del solver 1D y análisis comparativo

### Changed
- `Runner.sweep()` calcula el flujo escalar y angular en la misma pasada; se
  eliminó el segundo recorrido por iteración (`calculo_flujo`).
- `Runner.calculo_flujo()` se conserva como API pública y quedó vectorizada
  con NumPy; coincide con la pasada única a 5.6 × 10⁻¹⁷.
- Los invariantes del barrido (`dx`, `σt`, `μ`, `|μ|`, `ω`, `θ`) se precalculan
  y ya no se consultan atributos ni `abs()` dentro del bucle interno.
- La tolerancia interna de scattering es `max(epsilon, TOL_K)`; con el default
  `epsilon=1e-5` reduce ~40 % los barridos sin cambiar `k_eff` de forma
  apreciable (≈1.6 × 10⁻⁵ en el benchmark de 20 cm).
- Las pruebas de regresión fijan `epsilon=1e-6` para conservar las referencias
  históricas de `k_eff` y de conteo de iteraciones.

### Added
- Switch **Power normalization** en la pestaña Config: `POWER_KW`, `E_F_MEV`,
  `NU` y `AREA_CM2` permanecen ocultos hasta activarlo; al activarlo
  `POWER_KW` es obligatorio y al cargar un JSON con `POWER_KW` se enciende
  solo.
- `extras/analisis_codigo.md`: comparación del solver S_N 1D con el solver
  JavaScript LabSN 1D, con 10 casos de prueba y balance de partículas.
- `extras/mejoras_nts.md`: diagnóstico de rendimiento (perfil, iteraciones,
  tiempos antes/después).
- `extras/propuesta_dsa_cmfd.md` y
  `extras/propuesta_barrido_vectorizado.md`: propuestas de aceleración de
  convergencia y de barrido vectorizado/compilado.

### Fixed
- `Use in Plots` cambia siempre a la pestaña Plots, aunque el panel se monte
  por primera vez; el archivo se aplica después de la composición y la
  navegación ya no depende de leer el JSON.
- Los paneles cargan sus datos con `call_after_refresh` desde `compose`, lo
  que elimina los `NoMatches` al consultar hijos todavía no compuestos.

### Performance
- Autovalor 20 cm S8 I=200: 2136 ms → 820 ms (2.6×).
- Resto de los casos: 1.4–1.7× con las mismas tolerancias.

## [3.9.0] - 2026-11-16 - TUI: refresco global, cancelación y estructura

### Added
- `NTSApp.refresh_all()` mantiene sincronizadas Dashboard, Config, Run,
  Results, Plots, Sweep y Export después de cada corrida.
- Hoja de estilos externa `tui/app.tcss`, incluida en el paquete.
- Log de diagnóstico en `outputs/logs/tui.log` con los tracebacks que la TUI
  solo mostraba como texto rojo.
- `Cancel` en Sweep y `LoadingIndicator` compartido con Run.
- Widget base `RowTable` y mixin `RunPanel` para no duplicar tablas ni
  manejo del subproceso.
- `tui/services/paths.py` centraliza numeración, nombres libres y anclaje de
  rutas relativas al directorio del proyecto.
- Configuración de `ruff` en `pyproject.toml` y pruebas de rutas, cancelación,
  refresco global y mapeo fila/run.

### Fixed
- `next_config_path` y `next_result_path` ya no pueden devolver un nombre
  existente (antes sobrescribían resultados al llegar a 1000 o al haber
  nombres no numéricos).
- El detalle de Results ya no falla cuando el payload contiene entradas que no
  son objetos.
- Las rutas relativas escritas en la TUI se resuelven contra la raíz del
  proyecto, no contra el directorio desde donde se lanzó.
- Cancelar espera al proceso y escala a `kill`; cerrar la TUI detiene la
  corrida en curso.
- Los valores `0` de iteraciones se muestran en vez de tratarse como ausentes.
- Las tablas aceptan placeholders en sus celdas.
- `parse_field` interpreta `"false"`/`"0"` como falso.

### Changed
- `MODE` se guarda siempre con un valor concreto en el JSON.
- El selector de runs de Plots usa índices, así que dos runs con el mismo
  `config_name` no se confunden.

## [3.8.1] - 2026-11-16 - Arranque rápido de la TUI

### Changed
- `tui.services` ya no importa `export` ni `plots` al iniciar.
- `Config`, `matplotlib`, `pandas` y `openpyxl` se cargan solo al usarlos.
- Results y Plots cargan sus datos al activar la pestaña, no en `on_mount`.
- `nts tui` evita importar `cli.commands`; `nts-tui` sigue siendo el atajo directo.

## [3.8.0] - 2026-11-16 - Fronteras escalares

### Added
- `bound_left` y `bound_right` aceptan un escalar o una lista de un elemento y
  lo expanden a `N/2` valores iguales.
- La TUI muestra la ayuda de expansión en los campos de flujo entrante.
- Las fronteras reflexivas ocultan el flujo entrante correspondiente.

### Fixed
- Un valor escalar en la frontera ya no falla con longitud incorrecta.
- El mensaje de error indica la longitud esperada y la recibida.

## [3.7.0] - 2026-11-16 - Geometría y materiales editables en la TUI

### Added
- Barra de geometría 1D coloreada por zona material.
- Tabla editable de regiones: `NC`, `HR`, `IZL` y `Q`.
- Tabla editable de zonas: `SCT` y `SCS`.
- Tabla de fisión por zona: `NU_SIGF` y `SIGMA_F`.
- Botones para agregar y quitar regiones y zonas.

### Changed
- `MODE` es el primer campo de la sección Physics.
- `fixed_source` oculta fisión y guarda `NU_SIGF` en cero.
- `eigenvalue` oculta `K_EFF`; `fixed_k` lo exige; `driven` usa `k=1`.
- Los campos de fisión y potencia solo aparecen en modos con fisión.
- `Q` se oculta en `eigenvalue` y se fuerza a cero.
- Se eliminaron las listas separadas por comas para geometría, materiales,
  fuente y fisión.
- Las gráficas angulares muestran todas las direcciones; se quitó `--directions`
  de la CLI y el selector de direcciones de la TUI.

## [3.6.0] - 2026-11-16 - TUI 1D

### Added
- `nts tui` y `nts-tui`: interfaz Textual para el flujo 1D completo.
- Pestañas Dashboard, Config, Run, Results, Plots, Sweep y Export.
- Wizard con todos los campos de `Config.manual_input`, incluyendo placeholders.
- Run manager con log en vivo, cancelación, salida JSON y Excel.
- Plot studio con scalar, angular, `k_history` y SCS; preview inline opcional.
- Sweep de placeholders con preview, guardado JSON/Python y corrida por lote.
- Exportación de `datos.json`, Excel y gráficas SCS.
- `tests/test_tui_services.py` y `tests/test_tui_app.py`.

### Changed
- Las reglas de placeholders se movieron a `core/placeholders.py` y las usan
  la CLI y la TUI.
- `textual` requiere `>=8,<9`.
- Extra opcional `images` con `textual-image` para preview inline.
- La pestaña Plots ya no permite elegir direcciones: el flujo angular siempre
  grafica todas sus componentes. Se eliminó `--directions` de `nts-1d-plot`.

## [3.5.0] - 2026-11-08 - Contadores de actualizaciones de flujo e iteraciones de autovalor

### Changed
- `iteration` se incrementa solo dentro de `check_convergence`, una vez por
  actualización de flujo completada (barrido derecho + izquierdo + recálculo
  del flujo escalar). Acumula entre iteraciones de potencia en eigenvalue.
- `iteration_eigenvalue` reporta las iteraciones de potencia (`null` fuera de
  eigenvalue); `outer_iterations` se mantiene como alias.
- La hoja `Runs` del Excel incluye `iteration_eigenvalue`.

## [3.4.0] - 2026-11-08 - Criterio de convergencia del flujo

### Changed
- `check_convergence` usa `max_i |1 - phi_new_i/phi_old_i|` con `|phi_old|`
  en el denominador (antes dividía por el flujo nuevo). Las celdas con
  `phi_old = 0` caen a diferencia absoluta.
- Documentado `epsilon = 1e-5` en modos de fuente fija y
  `min(epsilon, TOL_K) = 1e-6` en el flujo interno del autovalor.

### Added
- `Runner._relative_flux_change` y `tests/test_convergence.py` para la
  fórmula, el fallback con flujo nulo y flujos negativos.

## [3.3.0] - 2026-11-08 - NU por defecto para normalización de potencia

### Added
- `DEFAULT_NU = 2.49` (U-238, fisión rápida) se usa cuando `POWER_KW` está
  definido y no hay `SIGMA_F` ni `NU`.
- El wizard muestra el default en el prompt de `nu`; los configs JSON y
  `nts-1d-normalize` caen al default con un aviso.
- `SIGMA_F` mantiene prioridad sobre `NU`.

### Fixed
- El wizard ya no falla con "Value required" al dejar `nu` vacío durante la
  normalización de potencia.

## [3.2.0] - 2026-11-08 - Normalización de potencia

### Added
- Entrypoint `nts-1d-normalize`: escala un output consolidado existente a una
  potencia objetivo (`--power-kw`), con `--ef-mev`, `--area-cm2`, `--nu` y
  `--run`. `k_eff` no cambia; la salida es `<stem>_normalized.json` salvo
  que se indique `-o`.
- `power_unnormalized` (`P~`) en el JSON de cada run y en la hoja `Runs` del
  Excel.
- `solvers/runners/power.py`: helpers compartidos de integral de fisión,
  potencia y factor de escala.
- `doc/CALCULO_NORMALIZACION_1D_EN.md` y la guía española corregida.

### Changed
- `POWER_KW` registra `P~` y `C_N` (`power_unnormalized`, `power_scale`)
  junto a la potencia objetivo `power_w`.

## [3.1.0] - 2026-11-07 - Exportación a Excel

### Added
- Entrypoint `nts-1d-excel`: convierte un `output_1d_###.json` consolidado en
  un `.xlsx` formateado (Metadata, Runs, Zones, Regions, Boundaries,
  ScalarFlux, AngularFlux, Directions, k_history), con encabezados
  congelados, autofiltro y formatos numéricos.
- `nts-1d-run --excel [PATH]` escribe el libro junto al JSON.
- `runs[].source` en el JSON, con el origen de cada configuración.

## [3.0.0] - 2026-11-07 - Convención de flujo escalar y flujo angular direccional

### Changed (rompe el esquema de salida)
- `scalar_flux` es ahora la media angular `phi = 1/2 sum(omega * psi)` (los N
  pesos de la cuadratura suman 2), como en `doc/desc.md`. Las tasas de
  reacción (balance y potencia) usan `2*phi`; `k_eff` y la forma del flujo no
  cambian.
- `angular_flux` es `(NTC, N)`: `psi` media por celda y dirección, columnas
  por `mu` creciente. El campo de suma ponderada ya no se exporta (era
  redundante con `scalar_flux`).
- Cada run exporta además `miu` y `omega` (N ordenadas y pesos).
- `nts-1d-plot --kind angular` dibuja una línea por dirección con etiquetas
  `mu` y lee `miu` del run; los archivos viejos mantienen la etiqueta anterior.

## [2.10.0] - 2026-11-06 - Separación del solver y entrypoints por esquema

### Added
- Entrypoints `nts-1d-run-dd`, `nts-1d-run-step` y `nts-1d-run-sc` que fuerzan
  su esquema espacial (mismas flags que `nts-1d-run`).
- `spatial_schemes` a nivel de archivo en `output_1d_###.json` y `datos.json`;
  cada run mantiene su `spatial_scheme`.
- Fichas por método: `solvers/runners/NTS_DD_1D.md`,
  `NTS_STEP_1D.md` y `NTS_SC_1D.md`.
- `solvers/runners/scheme.py` (Method, protocolo `Scheme`, dispatch),
  `config.py`, `runner.py`, `NTS_STEP_1D.py` y `NTS_SC_1D.py`.
  `NTS_DD_1D.py` queda con el esquema DD y la fachada de compatibilidad.

### Changed
- `Config` es agnóstico del esquema; los pesos característicos pasan a
  `StepCharacteristic.prepare()`.
- El motor de transporte es único y recibe el esquema por el protocolo
  `Scheme`; `Runner(conf, scheme=...)` permite inyectarlo.
- `main.py` pasa a `cli.main`; `solvers` queda empaquetado, así que el CLI y
  los módulos del solver funcionan fuera de la raíz del repo.

### Fixed
- `nts` fallaba con `ModuleNotFoundError: No module named 'main'`.
- Encabezados y avisos de consola traducidos (`BOUNDARY CONDITIONS`,
  `EXTERNAL SOURCE`, `Warning: no data for S...`) y la suite ya no imprime
  salida de producto.
- `import solvers...` fallaba al ejecutar desde otro directorio.

## [2.9.0] - 2026-11-03 - Esquemas espaciales DD / STEP / SC

### Added
- `SPATIAL_SCHEME` en la configuración 1D (`"DD"`, `"STEP"`, `"SC"`;
  por defecto `"DD"`).
- Kernels de celda `_cell_out_dd`, `_cell_out_step`, `_cell_out_sc`,
  `cell_out()` y `cell_average()` en `NTS_DD_1D.py`.
- `theta_step_characteristic()` con serie para `α < 1e-3` y rechazo de
  espesores ópticos negativos.
- `Config.theta_sc` precalculado una vez por corrida, con forma
  `(NTC, N_HALF)`.
- Prompt del esquema en el asistente manual y en `nts-1d-config`.
- `tests/test_spatial_schemes.py` (29 tests).
- `doc/SPATIAL_SCHEMES_EN.md` y `doc/SPATIAL_SCHEMES.md`.

### Changed
- `Method` usa valores string y `Config.method` pasa a ser una propiedad
  derivada de `SPATIAL_SCHEME` (una sola fuente de verdad).
- `Runner.sweep()` resuelve el kernel una vez y `calculo_flujo()` reconstruye
  las medias de celda con `cell_average()`.
- El resultado de cada corrida incluye `spatial_scheme`.
- `nts-1d-run` muestra el origen de la configuración y el nombre del run bajo
  el banner `--- STARTING CALCULATION ---`, p. ej.
  `Source: outputs/inputs/inputs.py | run config_dict_003`.
- El resumen y la confirmación del modo manual pasan a inglés
  (`--- CONFIGURATION SUMMARY ---`, `Run? (y/n) [y]:`).
- `nts-1d-plot`: los dos últimos mensajes de consola pasan a inglés, y
  `tests/test_plot_1d_flux.py` verifica que ejes, títulos y leyendas se
  rendericen en inglés.

### Notes
- DD es bit a bit idéntico a la versión anterior.
- STEP es de primer orden; en la malla de 100 celdas queda ~0.9% por debajo
  de DD (comportamiento esperado del esquema).
- Sin recorte ni restricciones de positividad: los flujos negativos de DD en
  celdas gruesas se reportan tal cual.

## [2.8.0] - 2026-11-02 - Salidas en inglés y documentación bilingüe

### Changed
- Todas las figuras, reportes y mensajes/prompts del CLI se generan en
  inglés.
- Traducidos `plot_1d_flux`, `sweep_kpis`, la consola del solver, el
  generador de configs y los mensajes de `nts-1d-data`.
- La documentación principal tiene versión en inglés; las versiones en
  español se mantienen.

### Added
- `doc/MULTIPLICATIVE_MEDIA_EN.md` (versión inglesa).
- `doc/desc_EN.md` (versión inglesa).
- `Changelog_EN.md` actualizado con las entradas 2.x.
- Versión del proyecto a 2.8.0.

## [2.7.0] - 2026-11-02 - Placeholders en geometría 1D

### Added
- `nts-1d-config` acepta placeholders en `NC` (celdas) y `HR` (espesor).
- `Config.auto_input` valida que `NC` e `IZL` sean enteros positivos y que
  `HR` sea finito y positivo.
- Tests de generación/expansión con placeholders espaciales y rechazo de
  `NC` no entero.

### Changed
- `NC` con placeholder debe expandirse a enteros positivos; `N`, `IZL` y
  `MAX_OUTER` siguen siendo numéricos.
- README, QUICKSTART, QUICK_REFERENCE, MULTIPLICATIVE_MEDIA y skill
  actualizados.
- Versión del proyecto a 2.7.0.

## [2.6.0] - 2026-11-02 - Comando `nts-1d-config`

### Changed
- El entry point del generador de configs 1D pasa a llamarse
  `nts-1d-config`.
- README, QUICKSTART, QUICK_REFERENCE, NTS_DOCUMENTATION,
  MULTIPLICATIVE_MEDIA, skill y tests actualizados con el nuevo nombre.
- Versión del proyecto a 2.6.0.

## [2.5.0] - 2026-11-02 - Entry point `nts-test`

### Added
- `nts-test`: ejecuta la suite `unittest` del repositorio desde cualquier
  cwd, con `-v`, `--failfast`, `-p/--pattern` y `--start-dir`.
- `tests/test_run_tests.py` (2 tests; 48 en total).
- README, QUICKSTART, QUICK_REFERENCE, MULTIPLICATIVE_MEDIA y la skill
  actualizados para usar `nts-test`.

### Changed
- Versión del proyecto a 2.5.0.

## [2.4.0] - 2026-11-02 - Generador de configs 1D con placeholders

### Added
- `nts-1d-config`: asistente interactivo que escribe
  `outputs/inputs/config_1d_###.json` (auto-numerado) o `-o`.
- Placeholders directos en los prompts (`kk`, `mm`, ...) en los campos
  físicos; el JSON guarda esos nombres como strings.
- `nts-generate --json INPUT --place-holder ... -o OUTPUT`: expansión de
  placeholders desde JSON a `.json` (lista de configs) o `.py`
  (`config_dict_###` / `inputs.py`).
- Validación de cada config 1D expandida con `Config(manual=False, **cfg)`.
- 9 tests nuevos (46 en total).
- README, QUICKSTART, NTS_DOCUMENTATION, QUICK_REFERENCE,
  MULTIPLICATIVE_MEDIA y la skill `nts-pinns-autopilot` actualizados.

### Changed
- `Config` acepta `allow_placeholders`; `_prompt_number` permite números o
  nombres; se omite la validación numérica/preliminar si hay placeholders.
- `nts-generate` acepta `--json` y `-o`; sin `-o` sigue escribiendo
  `outputs/inputs/inputs.py`.
- Versión del proyecto a 2.4.0.

### Fixed
- El redondeo de la expansión ya no destruye valores como `TOL_K=1e-6`;
  solo se redondean los valores inyectados por los placeholders.
- `nts generate` (CLI principal) añade el repo root a `sys.path` para poder
  validar configs 1D.

## [2.3.0] - 2026-11-01 - Gráficos de flujo 1D

### Added
- `utils/plot_1d_flux.py` y `nts-1d-plot` aceptan `-r output_1d_*.json`
  con `--kind scalar|angular|k-history|scs`.
- Flujo escalar vs `x`, flujo angular por dirección en un solo eje con
  colores y leyendas diferenciadas, y `k_history` vs iteración exterior.
- `--run`/`--list-runs` para seleccionar runs; `--run all` para
  `scalar`/`k-history`; `--directions` para elegir direcciones angulares.
- 13 tests nuevos (37 en total).
- README, QUICKSTART, NTS_DOCUMENTATION, QUICK_REFERENCE,
  MULTIPLICATIVE_MEDIA y la skill `nts-pinns-autopilot` actualizados.

### Changed
- `nts-1d-plot` apunta a `utils.plot_1d_flux:main`;
  `utils/plot_scs_flux.py` queda como implementación legada.
- Versión del proyecto a 2.3.0.

### Fixed
- Al graficar `angular_flux` se descarta la fila extra
  `NTP = NTC + 1` que el solver guarda sin usar.

## [2.2.0] - 2026-11-01 - Configuración manual y JSON (1D)

### Added
- `nts-1d-run --manual` / `nts run-1d --manual`: asistente interactivo paso
  a paso (geometría, materiales, cuadratura, fisión con `NU_SIGF`, `MODE`,
  `K_EFF`, `TOL_K`/`MAX_OUTER`/`K0`, potencia y fronteras), con resumen y
  confirmación antes de ejecutar.
- `nts-1d-run --json` / `nts run-1d --json`: carga uno o varios dicts 1D
  desde un archivo JSON (objeto o lista).
- `Config.as_dict()`: configuración efectiva serializable.
- Los outputs embeben `configuration`; `nts-1d-data` y `sweep_kpis.py` la
  usan sin depender de `outputs/inputs/inputs.py`.
- 15 tests nuevos (manual y JSON); 24 en total.
- `SKILL.md`, `evals.json`, README, QUICKSTART, NTS_DOCUMENTATION,
  QUICK_REFERENCE y MULTIPLICATIVE_MEDIA actualizados.

### Changed
- `manual_input` pregunta `Q` después de conocer el `MODE` (se omite en
  `eigenvalue`) y pide las fronteras dentro del asistente.
- `--manual`, `--json` y `-c` son mutuamente excluyentes.
- Versión del proyecto a 2.2.0.

### Fixed
- `nts-1d-data` puede extraer flujos de runs manuales/JSON usando la
  configuración embebida.

## [2.1.0] - 2026-11-01 - Medios multiplicativos y k_eff (1D)

### Added
- `NTS_DD_1D` resuelve fisión isotrópica con `NU_SIGF` (νΣf) y cuatro
  modos: `fixed_source`, `eigenvalue`, `fixed_k` y `driven`.
- Power iteration para `k_eff` en `MODE=eigenvalue`, con `TOL_K`,
  `MAX_OUTER`, `K0` e historial `k_history`.
- Balance global `k_balance = P/(A+L)` con fuga neta (saliente − entrante).
- Normalización opcional por potencia: `POWER_KW`, `E_F_MEV`, `NU`,
  `AREA_CM2` y `SIGMA_F`.
- Salida JSON enriquecida: `mode`, `k_eff`, `k_balance`, `k_history`,
  `k_converged`, `outer_iterations`, `power_w`, `power_scale`.
- `nts-1d-data` propaga `NU_SIGF`, `mode`, `k_eff` y `k_balance` a
  `datos.json`.
- `nts-1d-plot --x {SCS,NU_SIGF,k_eff}`.
- `skills/nts-pinns-autopilot/scripts/sweep_kpis.py` incluye tabla de
  `k_eff`.
- Tests `tests/test_dd_1d_fission.py` (medio infinito reflectivo,
  benchmark de 20 cm, `fixed_k` en `k*`, `driven`, potencia, regresión y
  validaciones).
- Guía `doc/MULTIPLICATIVE_MEDIA.md`.
- README, QUICKSTART, NTS_DOCUMENTATION, QUICK_REFERENCE y la skill
  `nts-pinns-autopilot` actualizados.

### Changed
- `Config` 1D: fronteras por defecto a ceros de longitud `N/2`; validación
  de `MODE`, `NU_SIGF`, `K_EFF` y potencia.
- `MODE` se infiere si se omite, manteniendo compatibilidad con los
  configs existentes (`NU_SIGF=0` → `fixed_source`).
- Versión del proyecto a 2.1.0.

### Fixed
- Peso N=6 en `solvers/runners/cuadraturas.py`:
  `0.4679139345866910` → `0.4679139345726910`.
- Fronteras mixtas (reflexiva/vacío): se respeta el flujo entrante de
  `bound_left`/`bound_right`; antes se sobrescribía con `1.0`.

### Notes
- Los solvers 2D en C siguen siendo de fuente fija; no aceptan `NU_SIGF`
  ni `k_eff`.

## [2.0.0] - 2026-09-14 - Documentación y Consistencia

### Added
- README.md completamente reescrito en inglés con referencia completa de comandos, arquitectura y flujos de trabajo
- `nts-1d-plot` ahora acepta `-i/--input` y `-o/--output` y descubre dinámicamente las posiciones de flujo (`flux_*`) en `datos.json`

### Changed
- Versión alineada a 2.0.0 en `pyproject.toml` y `README.md` (antes 0.1.0 vs 1.3.1)
- `QUICKSTART.md`, `IMPLEMENTATION_SUMMARY.md` y `FIXES_APPLIED.md` movidos a `doc/`
- `doc/NTS_DOCUMENTATION.md` ahora referencia los 5 programas (incluyendo `NTS_STEP`)
- `run-1d --output` help corregido: el default es `output_1d_###.json` auto-numerado

### Fixed
- `run_batch` y `run_solver_comparison` en `execution/parallel.py` ahora escriben `output_*.json` (antes `.txt`)
- `doc/example_imput.txt` renombrado a `doc/example_input.txt`

---

## [1.2.0] - 2026-03-30 - Actualización y Refinamiento

### Added
- Defaults explícitos en help de argumentos CLI
- .gitignore completo para archivos generados
- Archivos .gitkeep para mantener estructura de directorios

### Changed
- Imports de `json` movidos al inicio de config.py
- Help de argumentos ahora muestra valores por defecto

### Improved
- Documentación actualizada con todos los cambios
- Código más limpio y mantenible

---

## [1.3.0] - 2026-05-26 - Graficado de MFLUX y Empaquetado CLI

### Added
- Nuevo comando CLI `plot` para graficar MFLUX en 2D con barra de color
- Directorio de plots `outputs/results/plots/` y numeración automática de imágenes
- Dependencia de `matplotlib` para generación de gráficos

### Changed
- Configuración de empaquetado con `build-system` y `tool.uv.package` para habilitar entry points
- Inclusión explícita de paquetes y módulo `main` en configuración de setuptools
- Resultados de `run` ahora se guardan como `output_*.json`

### Fixed
- Entrada `nts` ahora funciona con `uv run nts ...`

---

## [1.3.1] - 2026-06-01 - CLI 1D y Placeholders

### Added
- Comando CLI `run-1d` para ejecutar el solver `NTS_DD_1D` y guardar resultados JSON consolidados
- Soporte `generate --place-holder` para crear `outputs/inputs/inputs.py` desde `inputs_placeholder.py`
- Script `utils/plot_scs_flux.py` para graficar SCS vs flujo escalar (posiciones 0 y 99)
- Script `utils/extract_1d_flux.py` para extraer flujos escalares a `datos.json`
- Atajos: `nts-1d-data`, `nts-1d-plot`, `nts-1d-run`, `nts-generate`

### Changed
- Outputs 1D numerados como `output_1d_###.json`

---

## [1.1.0] - 2026-03-30 - Correcciones Post-Implementación

### Removed
- **TUI completa eliminada** - Sistema ahora es CLI-only
- **Output parser eliminado** - Solvers producen JSON directamente

### Changed
- **Logging menos verboso** - Console nivel WARNING, archivos DEBUG
- **Ejecución de solvers corregida** - De stdin a argumento: `NTS_DD input.txt`
- Simplificado `main.py` (sin router TUI)
- Simplificado `cmd_show` para leer JSON directo

### Fixed
- Solvers ahora producen outputs JSON válidos (~890KB)
- Sin mensajes INFO innecesarios en consola
- Ejecución correcta: `subprocess.run([solver_path, input_path])`

### Documentation
- README.md actualizado sin TUI
- QUICKSTART.md simplificado (solo CLI)
- IMPLEMENTATION_SUMMARY.md con arquitectura actual
- FIXES_APPLIED.md con log de correcciones

---

## [1.0.0] - 2026-03-30 - Implementación Inicial

### Added
- ✅ Sistema completo de automatización NTS
- ✅ Módulos core: config.py, validator.py, input_builder.py
- ✅ Execution: runner.py, parallel.py, output_parser.py (luego eliminado)
- ✅ CLI: 6 comandos (status, validate, generate, run, list, show)
- ✅ TUI: 4 pantallas + widgets (luego eliminado)
- ✅ Utils: logger.py, paths.py
- ✅ Templates: base_input.json
- ✅ Documentación completa

### Features
- Generación de input.txt con validación física estricta
- Validación robusta (N par, σ_s < σ_t, rangos, dimensiones)
- Ejecución paralela con multiprocessing
- 4 solvers soportados: NTS_DD, NTS_LD, NTS_RM_CN, NTS_RM_LLN
- Logging completo con métricas
- Sistema de paths centralizado

### Tests
- ✅ 23/23 tareas completadas
- ✅ Inputs generados exitosamente
- ✅ Todos los comandos CLI funcionando
- ✅ Solvers detectados correctamente

---

## Notas de Versión

### v1.2.0 - Refinamiento
Pequeñas mejoras de calidad de código y documentación. Sistema más pulido.

### v1.1.0 - Correcciones Críticas
Eliminación de TUI y output parser para simplificar el sistema. Corrección crítica en ejecución de solvers.

### v1.0.0 - MVP Completo
Primera versión funcional con todas las características principales implementadas.

---

## Formato

Este changelog sigue [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y el proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Tipos de Cambios
- **Added** - Nuevas características
- **Changed** - Cambios en funcionalidad existente
- **Deprecated** - Funcionalidad que será eliminada
- **Removed** - Funcionalidad eliminada
- **Fixed** - Corrección de bugs
- **Security** - Parches de seguridad
