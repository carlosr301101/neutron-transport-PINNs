# Instalación

Guía para instalar `neutron-transport-pinns` desde PyPI, desde un wheel local
o desde el repositorio.

> El paquete de PyPI incluye la CLI, la TUI y el solver 1D en Python.
> Los solvers 2D en C no se incluyen en el wheel. Para usarlos hay que clonar
> el repositorio y compilar los binarios.

## Requisitos

- Python **3.14 o superior**.
- Uno de estos gestores:
  - [uv](https://docs.astral.sh/uv/) (recomendado),
  - `pip`.
- Linux, macOS o Windows.

Comprobar Python:

```bash
python --version
```

## Instalación con uv

### Comando aislado

```bash
uvx --from neutron-transport-pinns nts --help
uvx --from neutron-transport-pinns nts-tui
```

### Instalación permanente

```bash
uv tool install neutron-transport-pinns
```

Verificar:

```bash
nts --help
nts status
nts-tui
```

Actualizar:

```bash
uv tool upgrade neutron-transport-pinns
```

Desinstalar:

```bash
uv tool uninstall neutron-transport-pinns
```

### Preview de imágenes en la TUI

El preview inline es opcional:

```bash
uv tool install "neutron-transport-pinns[images]"
```

Requiere una terminal compatible con Kitty, WezTerm, iTerm2 o sixel. Si no hay
soporte, la TUI genera el PNG y ofrece abrirlo externamente.

## Instalación con pip

```bash
python -m pip install neutron-transport-pinns
```

Con preview de imágenes:

```bash
python -m pip install "neutron-transport-pinns[images]"
```

Verificar:

```bash
nts --help
nts status
nts-tui
```

Actualizar:

```bash
python -m pip install --upgrade neutron-transport-pinns
```

Desinstalar:

```bash
python -m pip uninstall neutron-transport-pinns
```

En Windows, si `python` no apunta a 3.14:

```powershell
py -3.14 -m pip install neutron-transport-pinns
```

## Primer uso

La CLI y la TUI escriben en `outputs/` dentro del directorio actual. Se puede
elegir otro directorio:

```bash
export NTS_HOME="$HOME/nts-work"     # Linux/macOS
set NTS_HOME=%USERPROFILE%\nts-work  # Windows cmd
```

Crear una configuración 1D:

```bash
nts-1d-config -o outputs/inputs/config_1d_001.json
```

Ejecutarla:

```bash
nts-1d-run --json outputs/inputs/config_1d_001.json
```

Abrir la TUI:

```bash
nts-tui
```

La TUI permite crear la configuración, correr el solver 1D, ver resultados,
generar plots, hacer sweeps y exportar datos.

## Instalación desde un wheel local

```bash
uv build --clear
uv pip install dist/*.whl
```

O con pip:

```bash
python -m pip install dist/*.whl
```

## Instalación para desarrollo

```bash
git clone https://github.com/carlosr301101/neutron-transport-PINNs.git
cd neutron-transport-PINNs
uv sync
```

Con preview de imágenes:

```bash
uv sync --extra images
```

Comandos de desarrollo:

```bash
uv run nts --help
uv run nts-tui
uv run python -m cli.run_tests
uv run python -m cli.run_tests -v
```

`nts-test` es un comando de desarrollo del repositorio y no se incluye en el
wheel publicado.

## Solvers 2D

El wheel de PyPI no contiene:

- `NTS_DD`
- `NTS_LD`
- `NTS_STEP`
- `NTS_RM_CN`
- `NTS_RM_LLN`
- las fuentes `.c` y `.h`

Para el flujo 2D:

1. Clonar el repositorio.
2. Compilar los binarios en `solvers/runners/`.
3. Indicar la ruta si no están en el layout del repo:

```bash
export NTS_SOLVERS_DIR="$HOME/nts-solvers"  # Linux/macOS
set NTS_SOLVERS_DIR=%USERPROFILE%\nts-solvers  # Windows cmd
```

`nts status` informa qué binarios faltan.

## Problemas comunes

| Síntoma | Solución |
|---|---|
| `python: command not found` | Instalar Python 3.14 o usar `py -3.14` en Windows |
| `nts: command not found` | Ejecutar `uv tool install` o `pip install` y revisar el `PATH` |
| `nts-tui` no abre | Verificar que la terminal soporte Textual; usar una terminal moderna |
| No se ve el preview inline | Instalar `[images]` y usar Kitty/WezTerm/iTerm2/sixel |
| `nts run` dice solver missing | Compilar los binarios 2D y configurar `NTS_SOLVERS_DIR` |
| `nts-test` no existe | Es un comando de desarrollo; usar `uv run python -m cli.run_tests` |
| `outputs/` aparece en una ruta inesperada | Definir `NTS_HOME` o ejecutar desde el directorio de trabajo deseado |
