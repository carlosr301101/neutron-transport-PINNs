# Changelog

Registro de todos los cambios notables en el proyecto NTS Automation System.

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
