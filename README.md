# NTS Automation System

Sistema CLI de automatización para simulaciones de transporte de neutrones (NTS) con ejecución paralela y gestión robusta de configuraciones.

## 🚀 Características

- ✅ **Generación automática de archivos input.txt** con validación física estricta
- ✅ **CLI completo** para operaciones batch y scripting
- ✅ **Ejecución paralela** de múltiples simulaciones
- ✅ **Validación robusta** de configuraciones antes de ejecutar
- ✅ **Outputs JSON directo** desde solvers (sin parsing adicional)
- ✅ **Sistema de logging** con métricas y logs detallados
- ✅ **Gestión de múltiples solvers** (NTS_DD, NTS_LD, NTS_RM_CN, NTS_RM_LLN)
- ✅ **Solver por defecto** (NTS_DD) - no es necesario especificar siempre

## 📋 Requisitos

- Python 3.14+
- uv (gestor de paquetes)
- Binarios NTS compilados en `solvers/runners/`

## 🔧 Instalación

```bash
# Instalar dependencias con uv
uv sync

# Verificar instalación
uv run python main.py status
```

## 🎯 Uso

### Comandos Disponibles

#### 1. Ver estado del sistema
```bash
uv run python main.py status
```

#### 2. Validar configuración
```bash
uv run python main.py validate templates/base_input.json
```

#### 3. Generar archivo input.txt
```bash
# Generar desde configuración JSON
uv run python main.py generate templates/base_input.json

# Con preview
uv run python main.py generate templates/base_input.json --preview
```

#### 4. Listar archivos
```bash
# Listar inputs generados
uv run python main.py list inputs

# Listar resultados
uv run python main.py list outputs
```

#### 5. Ejecutar simulaciones
```bash
# Ejecutar con solver específico
uv run python main.py run --solver NTS_DD

# Ejecutar inputs específicos
uv run python main.py run -i outputs/inputs/input_001.txt

# Ejecutar en paralelo (4 procesos)
uv run python main.py run --solver NTS_DD --parallel 4
```

#### 6. Ver resultados
```bash
# Ver archivo de salida
cat outputs/results/output_001.txt

# La salida es JSON con STATUS, ITER, MFLUX, MFLOW, etc.
```

## 📁 Estructura del Proyecto

```
neutron-transport-PINNs/
├── main.py                      # Entry point CLI
├── core/                        # Generación y validación
├── execution/                   # Ejecución de solvers
├── cli/                         # Interfaz CLI
├── utils/                       # Utilidades
├── templates/                   # Plantillas de configuración
├── outputs/                     # Outputs del sistema
│   ├── inputs/                 # Archivos input_XXX.txt
│   ├── results/                # Archivos output_XXX.txt (JSON)
│   └── logs/                   # Logs de simulaciones
└── solvers/
    └── runners/                # Binarios NTS
```

## 📝 Formato de Configuración

Ver `templates/base_input.json` para un ejemplo completo con comentarios.

Parámetros principales:
- **N**: Ordenadas discretas (par)
- **NZ**: Número de zonas
- **zones**: Secciones eficaces (σ_s < σ_t)
- **XDOM, YDOM**: Geometría del dominio
- **ZMAP**: Mapa de materiales
- **QMAP**: Mapa de fuentes
- **BC**: Condiciones de frontera
- **TOL**: Tolerancia de convergencia

## 🔄 Workflow Típico

1. **Crear/editar configuración** en JSON
2. **Validar** configuración
3. **Generar** archivos input.txt
4. **Ejecutar** simulaciones en paralelo
5. **Analizar** resultados JSON

## 📊 Formato de Salida

Los solvers generan salida JSON con:
- `STATUS`: Código de estado (0 = éxito)
- `ITER`: Número de iteraciones
- `CPU`: Tiempo de CPU
- `MFLUX`: Matriz de flujos medios
- `MFLOW`: Matrices de flujos direccionales

Ejemplo:
```json
{
  "STATUS": 0,
  "ITER": 20,
  "CPU": -0.999,
  "MFLUX": [[...], [...]],
  "MFLOW": [[[...]], [[...]]]
}
```

## 🐛 Troubleshooting

```bash
# Verificar solvers disponibles
uv run python main.py status

# Ver logs detallados
cat outputs/logs/simulation_*.log

# Ver logs del sistema
cat outputs/logs/nts_automation_*.log
```

## 📚 Ayuda

```bash
# Ayuda general
uv run python main.py --help

# Ayuda de comando específico
uv run python main.py [command] --help
```

## 📂 Gestión del Repositorio

### Archivos Ignorados

El `.gitignore` está configurado para ignorar archivos generados que no son necesarios para correr el sistema:

- ✅ **Outputs generados**: `outputs/inputs/*.txt`, `outputs/results/*.txt`, `outputs/logs/*.log`
- ✅ **Cache de Python**: `__pycache__/`, `*.pyc`
- ✅ **Entornos virtuales**: `.venv/`, `venv/`
- ✅ **Archivos de IDE**: `.vscode/`, `.idea/`
- ✅ **Temporales**: `*.tmp`, `*.bak`, `Notas.md`

La estructura de directorios se mantiene con archivos `.gitkeep` en `outputs/`.

---

**NTS Automation System** - Automatización de simulaciones de transporte de neutrones 🚀
