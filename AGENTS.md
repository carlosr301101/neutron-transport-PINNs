# AGENTS.md

## Automatización de Simulación NTS con Python + TUI + Ejecución Paralela

---

## 1. Objetivo del sistema

Construir un sistema en Python que permita:

1. Generar archivos `input.txt` válidos para los solvers NTS.
2. Gestionar múltiples inputs definidos manualmente o desde TUI.
3. Ejecutar solvers en C automáticamente.
4. Paralelizar ejecuciones.
5. Proveer una interfaz TUI para interacción.

---

## 1.1 Preparando el proyecto de python

1. Deberas usar uv como principal gestor de paquetes.
2. todo los modulos necesarios para el proyecto deberan ser instalados usando uv, como por ejemplo textual para la parte de TUI.
3. Para ejecutar cualquier script tiene que ser ejecutado usando uv, por ejemplo: `uv run main.py`.

## 2. Arquitectura del sistema

```
nts_automation/
│
├── main.py                  # Entry point
├── tui/
│   └── app.py              # Interfaz TUI
│
├── core/
│   ├── input_builder.py    # Generación de input.txt
│   ├── validator.py        # Validación física y estructural
│
├── execution/
│   ├── runner.py           # Ejecución de solvers
│   ├── parallel.py         # Paralelización
│
├── templates/
│   └── base_input.json     # Config base editable
│
├── outputs/
│   ├── inputs/
│   ├── results/
│
└── solvers/
    ├── NTS_DD
    ├── NTS_LD ├── NTS_RM_CN
    ├── NTS_RM_LLN
```

---

## 3. Formato del input

El archivo `input.txt` debe seguir estrictamente:

```
Line 1: N
Line 2: NZ
Lines: σ_t σ_s
Line: NR_X
Lines: XDOM
Line: NR_Y
Lines: YDOM
Lines: ZMAP
Lines: QMAP
Line: BC
Line: TOL
```

Ejemplo base:

```
4
1
0.5 0.3
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 1
1 1
1.0 1.0
1.0 1.0
0.0 0.0 0.0 0.0
1e-5
```

---

## 4. Módulo: Generador de Input

### `core/input_builder.py`

```python
class InputBuilder:
    def __init__(self, config: dict):
        self.config = config

    def build(self) -> str:
        lines = []

        lines.append(str(self.config["N"]))
        lines.append(str(self.config["NZ"]))

        for zone in self.config["zones"]:
            lines.append(f"{zone['sigma_t']} {zone['sigma_s']}")

        lines.append(str(self.config["NR_X"]))
        for x in self.config["XDOM"]:
            lines.append(f"{x['length']} {x['nodes']}")

        lines.append(str(self.config["NR_Y"]))
        for y in self.config["YDOM"]:
            lines.append(f"{y['length']} {y['nodes']}")

        for row in self.config["ZMAP"]:
            lines.append(" ".join(map(str, row)))

        for row in self.config["QMAP"]:
            lines.append(" ".join(map(str, row)))

        lines.append(" ".join(map(str, self.config["BC"])))
        lines.append(str(self.config["TOL"]))

        return "\n".join(lines)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.build())
```

---

## 5. Módulo: Validación

### `core/validator.py`

```python
def validate(config):
    assert config["N"] % 2 == 0, "N debe ser par"

    for z in config["zones"]:
        assert z["sigma_s"] < z["sigma_t"], "σ_s < σ_t requerido"

    for row in config["ZMAP"]:
        for val in row:
            assert 1 <= val <= config["NZ"]

    for row in config["QMAP"]:
        for val in row:
            assert val >= 0

    tol = config["TOL"]
    assert 1e-7 <= tol <= 1e-2
```

---

## 6. Gestión de múltiples inputs

El sistema debe permitir manejar múltiples configuraciones definidas por el usuario.

### Estrategia

* Cada input se genera desde una configuración independiente
* Se almacenan en:

```
outputs/inputs/input_001.txt
outputs/inputs/input_002.txt
...
```

### Ejemplo

```python
configs = [config1, config2, config3]

for i, cfg in enumerate(configs):
    validate(cfg)
    builder = InputBuilder(cfg)
    builder.save(f"outputs/inputs/input_{i:03d}.txt")
```

---

## 7. Ejecución de Solvers

### `execution/runner.py`

```python
import subprocess
import json

def run_solver(executable, input_file, output_file):
    with open(output_file, "w") as out:
        subprocess.run(
            [executable, input_file],
            stdout=out,
            stderr=subprocess.PIPE
        )

def parse_output(path):
    with open(path) as f:
        return json.load(f)
```

---

## 8. Paralelización

### `execution/parallel.py`

```python
from multiprocessing import Pool
from execution.runner import run_solver

def _task(args):
    exe, inp, out = args
    run_solver(exe, inp, out)

def run_parallel(tasks, nproc=4):
    with Pool(nproc) as p:
        p.map(_task, tasks)
```

---

## 9. Interfaz TUI

### Librería recomendada

```
pip install textual
```

### `tui/app.py`

```python
from textual.app import App
from textual.widgets import Button, Input, Static

class NTSApp(App):

    def compose(self):
        yield Static("NTS Automation")
        yield Input(placeholder="N (even)")
        yield Button("Generate Input")
        yield Button("Run Simulations")

    def on_button_pressed(self, event):
        if event.button.label == "Generate Input":
            self.generate_input()

        elif event.button.label == "Run Simulations":
            self.run_simulations()

    def generate_input(self):
        # Crear configuración desde inputs de usuario
        # Validar
        # Guardar input.txt
        pass

    def run_simulations(self):
        # Detectar todos los inputs en outputs/inputs/
        # Ejecutar en paralelo
        pass
```

---

## 10. Flujo completo

Pipeline del sistema:

1. Usuario define parámetros en TUI
2. Se genera configuración
3. Se valida
4. Se guarda `input.txt`
5. Se repite para múltiples inputs si se desea
6. Se listan todos los inputs
7. Se preparan tareas:

   ```
   (solver, input, output)
   ```

8. Se ejecutan en paralelo
9. Se almacenan resultados

---

## 11. Ejemplo de ejecución paralela

```python
tasks = []

for i in range(10):
    tasks.append((
        "./solvers/NTS_LD",
        f"outputs/inputs/input_{i:03d}.txt",
        f"outputs/results/output_{i:03d}.json"
    ))

run_parallel(tasks, nproc=4)
```

---

## 12. Buenas prácticas

### Validación estricta

* Nunca ejecutar sin validar
* Evitar errores del solver

### Organización

```
inputs → outputs/inputs/
results → outputs/results/
```

### Naming consistente

```
input_001.txt
output_001.json
```

### Logging (recomendado)

* Tiempo de ejecución
* Solver usado
* Estado (STATUS)

---

## 13. Extensiones futuras

* Integración con PINNs (dataset)
* Dashboard de resultados
* Comparación automática entre solvers
* CLI adicional

---

## 14. Resultado esperado

El sistema final debe permitir:

✔ Crear inputs desde TUI
✔ Gestionar múltiples simulaciones
✔ Ejecutar en paralelo
✔ Obtener outputs estructurados
✔ Servir como base para pipelines científicos

---

Si el siguiente paso es útil, puedo construirte directamente el **código completo funcional listo para ejecutar**, incluyendo:

* TUI real con formularios completos
* CLI alternativa
* Integración directa con tus binarios NTS
* Sistema de logs y métricas listo para PINNs

Solo dime.
