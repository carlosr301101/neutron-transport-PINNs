# NTS Automation System

Versión: 1.3.1

Sistema CLI de automatización para simulaciones de transporte de neutrones (NTS) con ejecución paralela, gestión robusta de configuraciones, solver 1D Python y herramientas de post-procesado.

## 🚀 Características

- ✅ **Generación automática de archivos input.txt** con validación física estricta
- ✅ **CLI completo** para operaciones batch y scripting
- ✅ **Ejecución paralela** de múltiples simulaciones
- ✅ **Validación robusta** de configuraciones antes de ejecutar
- ✅ **Outputs JSON directo** desde solvers (sin parsing adicional)
- ✅ **Sistema de logging** con métricas y logs detallados
- ✅ **Gestión de múltiples solvers** (NTS_DD, NTS_LD, NTS_RM_CN, NTS_RM_LLN)
- ✅ **Solver 1D Python** (`NTS_DD_1D`) con Diamond Difference
- ✅ **Generación con placeholders** para barridos paramétricos
- ✅ **Atajos CLI** para flujos 1D
- ✅ **Post-procesado**: extracción de datos y ploteo automático

## 📋 Requisitos

- Python 3.14+
- uv (gestor de paquetes)
- Binarios NTS compilados en `solvers/runners/` (para solver 2D)
- Solver 1D Python integrado en `solvers/runners/NTS_DD_1D.py`

## 🔧 Instalación

```bash
# Instalar dependencias con uv
uv sync

# Verificar instalación
uv run nts status
```

## 🎯 Uso

### Comandos Disponibles

#### 1. Ver estado del sistema
```bash
uv run nts status
```

#### 2. Validar configuración
```bash
uv run nts validate templates/base_input.json
```

#### 3. Generar archivo input.txt
```bash
# Generar desde configuración JSON
uv run nts generate templates/base_input.json

# Con preview
uv run nts generate templates/base_input.json --preview
```

#### 3.1 Generar inputs con placeholders (barrido paramétrico)
```bash
# Lee outputs/inputs/inputs_placeholder.py y genera outputs/inputs/inputs.py
uv run nts-generate --place-holder KK 0.1 0.95 0.05

# Múltiples placeholders en paralelo
uv run nts-generate --place-holder KK 0.1 0.95 0.05 --place-holder QQ 1 3 1
```

**Ejemplo de `inputs_placeholder.py`:**
```python
config_dict = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [100],
    "HR": [100],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [kk],   # placeholder
    "Q": [0],
    "N": 4,
}
```

El resultado es `outputs/inputs/inputs.py` con `config_dict_001`, `config_dict_002`, etc.

#### 4. Listar archivos
```bash
# Listar inputs generados
uv run nts list inputs

# Listar resultados
uv run nts list outputs
```

#### 5. Ejecutar simulaciones 2D (binarios)
```bash
# Ejecutar con solver específico
uv run nts run --solver NTS_DD

# Ejecutar inputs específicos
uv run nts run -i outputs/inputs/input_001.txt

# Ejecutar en paralelo (4 procesos)
uv run nts run --solver NTS_DD --parallel 4
```

#### 6. Ejecutar solver 1D (Python)
```bash
# Ejecuta todos los configs en outputs/inputs/inputs.py
uv run nts-1d-run
# o
uv run nts run-1d
```

Genera JSON consolidado en `outputs/results/output_1d_###.json` con `scalar_flux` y metadata por config.

#### 7. Ver resultados
```bash
# Ver archivo de salida del solver 2D
cat outputs/results/output_001.json

# La salida es JSON con STATUS, ITER, MFLUX, MFLOW, etc.
```

#### 8. Plotear MFLUX
```bash
uv run nts plot
uv run nts plot --result outputs/results/output_002.json --show
```

### ⚡ Atajos (entry points)

| Atajo | Descripción |
|-------|-------------|
| `nts-1d-data` | Extrae flujos escalares a `datos.json` desde outputs 1D |
| `nts-1d-plot` | Grafica SCS vs flujo escalar (posiciones 0 y 99) |
| `nts-1d-run` | Ejecuta el solver 1D para los configs en `inputs.py` |
| `nts-generate` | Genera `inputs.py` desde `inputs_placeholder.py` |

**Uso:**
```bash
uv run nts-1d-data --latest
uv run nts-1d-data --latest --positions 0 50 99
uv run nts-1d-plot
uv run nts-1d-run
uv run nts-generate --place-holder KK 0.1 0.95 0.05
```

## 📈 Post-procesado

### Extraer datos
```bash
uv run nts-1d-data --latest
```

Genera `outputs/results/datos.json` con `SCS` y `scalar_flux` en posiciones configurables.

### Graficar SCS vs Flujo
```bash
uv run nts-1d-plot
```

Genera PNG en `outputs/results/plots/scs_flux.png` con dos subplots (posición 0 y posición 99).

## 📁 Estructura del Proyecto

```
neutron-transport-PINNs/
├── main.py                      # Entry point CLI
├── cli/                         # Interfaz CLI
│   ├── commands.py             # Comandos principales
│   ├── run_1d.py               # Entry point: nts-1d-run
│   └── generate_placeholder.py # Entry point: nts-generate
├── core/                        # Generación y validación
├── execution/                   # Ejecución de solvers
├── utils/                       # Utilidades
│   ├── paths.py
│   ├── logger.py
│   ├── plot_scs_flux.py        # Plotear SCS vs flujo
│   └── extract_1d_flux.py      # Extraer datos 1D
├── templates/                   # Plantillas de configuración
├── outputs/                     # Outputs del sistema (gitignored)
│   ├── inputs/                 # Archivos input_XXX.txt, inputs.py
│   ├── results/                # Archivos output_*.json, datos.json
│   └── logs/                   # Logs de simulaciones
└── solvers/
    └── runners/                # Binarios NTS + solver Python 1D
        ├── NTS_DD_1D.py
        └── cuadraturas.py
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

### Formato 1D (solver Python)

Para `NTS_DD_1D`, los configs usan formato simplificado:
- `num_regions`, `num_zones`
- `NC`: celdas por región
- `HR`: espesores
- `IZL`: zonas de cada región
- `SCT`: sigma total por zona
- `SCS`: sigma scattering por zona
- `Q`: fuente por región
- `N`: orden de cuadratura
- `reflex_izq`, `reflex_der`: condiciones reflexivas
- `bound_left`, `bound_right`: condiciones de frontera

## 📊 Formato de Salida

### Solver 2D (binarios C)
```json
{
  "STATUS": 0,
  "ITER": 20,
  "CPU": -0.999,
  "MFLUX": [[...], [...]],
  "MFLOW": [[[...]], [[...]]]
}
```

### Solver 1D (Python)
```json
{
  "solver": "NTS_DD_1D",
  "runs": [
    {
      "config_name": "config_dict_001",
      "scalar_flux": [...],
      "iteration": 13,
      "converged": true,
      "timestamp": "2026-06-01T19:02:59"
    }
  ]
}
```

## 🔄 Workflow Típico

### Solver 2D
1. **Crear/editar configuración** en JSON
2. **Validar** configuración
3. **Generar** archivos input.txt
4. **Ejecutar** simulaciones en paralelo
5. **Analizar** resultados JSON

### Solver 1D
1. **Crear/editar** `outputs/inputs/inputs_placeholder.py` con placeholders
2. **Generar** variantes con `uv run nts-generate --place-holder ...`
3. **Ejecutar** con `uv run nts-1d-run`
4. **Extraer datos** con `uv run nts-1d-data --latest`
5. **Visualizar** con `uv run nts-1d-plot`

## 🐛 Troubleshooting

```bash
# Verificar solvers disponibles
uv run nts status

# Ver logs detallados
cat outputs/logs/nts_automation_*.log

# Verificar que el solver 1D genera resultados
uv run nts-1d-run

# Regenerar inputs desde placeholders
uv run nts-generate --place-holder KK 0.1 0.95 0.05
```

## 📚 Ayuda

```bash
# Ayuda general
uv run nts --help

# Ayuda de comando específico
uv run nts [command] --help
```

## 📂 Gestión del Repositorio

### Archivos Ignorados

El `.gitignore` está configurado para ignorar archivos generados:

- ✅ **Outputs generados**: `outputs/inputs/*.txt`, `outputs/results/*.json`, `outputs/logs/*.log`
- ✅ **Placeholders regenerables**: `outputs/inputs/inputs.py`, `inputs_placeholder.py`
- ✅ **Solver 1D outputs**: `resultados_runner_*.xlsx`, `Config.log`
- ✅ **Cache de Python**: `__pycache__/`, `*.pyc`
- ✅ **Entornos virtuales**: `.venv/`, `venv/`
- ✅ **Archivos de IDE**: `.vscode/`, `.idea/`
- ✅ **Temporales**: `*.tmp`, `*.bak`, `Notas.md`

La estructura de directorios se mantiene con archivos `.gitkeep` en `outputs/`.

---

**NTS Automation System** - Automatización de simulaciones de transporte de neutrones 🚀
