# Changelog

Registro de todos los cambios notables en el proyecto NTS Automation System.

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
