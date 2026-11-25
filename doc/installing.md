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

Crear un directorio de trabajo y un problema 1D de autovalor:

```bash
mkdir nts-demo
cd nts-demo
cat > quickstart.json <<'JSON'
{
  "num_regions": 1,
  "num_zones": 1,
  "NC": [20],
  "HR": [20.0],
  "IZL": [1],
  "SCT": [1.0],
  "SCS": [0.9],
  "NU_SIGF": [0.11],
  "Q": [0.0],
  "N": 8,
  "SPATIAL_SCHEME": "DD",
  "reflex_izq": false,
  "reflex_der": false,
  "bound_left": [0, 0, 0, 0],
  "bound_right": [0, 0, 0, 0],
  "MODE": "eigenvalue",
  "TOL_K": 1e-6,
  "MAX_OUTER": 200
}
JSON

nts-1d-run --json quickstart.json -o outputs/results/quickstart.json
```

El solver imprime la convergencia y escribe un JSON consolidado. Generar el
plot de `k_eff`:

```bash
nts-1d-plot -r outputs/results/quickstart.json --kind k-history
```

Plot por defecto:

```text
outputs/results/plots/k_history.png
```

Para este quickstart, el autovalor esperado es aproximadamente:

```text
k_eff ~= 1.0264
```

Para usar otro directorio de trabajo:

```bash
export NTS_HOME="$HOME/nts-work"     # Linux/macOS
set NTS_HOME=%USERPROFILE%\nts-work  # Windows cmd
```

La CLI y la TUI crean `outputs/` dentro de `NTS_HOME`, no dentro de
`site-packages`.

### Abrir la TUI

```bash
nts-tui
```

Flujo típico:

1. **Config**: geometría, materiales, modo, fuente y fronteras.
2. **Save**: escribe `outputs/inputs/config_1d_###.json`.
3. **Run**: ejecuta el solver 1D con log en vivo.
4. **Results**: revisa `k_eff`, iteraciones y convergencia.
5. **Plots**: scalar, angular, `k_history` o SCS.
6. **Placeholders/Export**: sweeps paramétricos, `datos.json`, Excel.

Salir con `q`. Si el comando no está en `PATH`:

```bash
python -m tui.app
```

### Salida esperada

- `nts status` debe mostrar los cinco solvers 2D como OK en Linux x86_64 y
  Windows amd64, porque esos wheels los incluyen. En macOS, ARM u otra
  plataforma hay que compilarlos y usar `NTS_SOLVERS_DIR`.
- `nts-1d-run` escribe `outputs/results/quickstart.json`.
- `nts-1d-plot` escribe `outputs/results/plots/k_history.png`.
- La TUI escribe configs en `outputs/inputs/` y resultados en
  `outputs/results/`.

### Consola de Windows

En Windows la CLI usa salida ASCII para evitar caracteres rotos en PowerShell
y en consolas con code page heredada (`cp1252`/`cp850`). El checkmark final se
imprime como `OK`:

```text
OK Completed 3 run(s). Output: outputs/results/output_1d_003.json
```

Para recuperar los glifos Unicode (`✓`, `✗`, `•`) en una terminal moderna:

```powershell
chcp 65001
$env:NTS_UNICODE = "1"
```

Para forzar ASCII en cualquier sistema:

```powershell
$env:NTS_ASCII = "1"
```

La TUI no se ve afectada: Textual escribe con su propio driver.

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

Los wheels de **Linux x86_64** y **Windows amd64** incluyen:

- `NTS_DD`
- `NTS_LD`
- `NTS_STEP`
- `NTS_RM_CN`
- `NTS_RM_LLN`

No hace falta compilar en esas plataformas; `nts status` debe listar los cinco
como OK. El sdist (macOS, ARM y otras plataformas) incluye las fuentes `.c` y
los scripts de build, pero no los binarios. En esas plataformas:

1. Clonar el repositorio.
2. Compilar los binarios en `solvers/runners/` con `make -C solvers rebuild` (Linux)
   o `solvers/build_windows.ps1` (Windows).
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
| `nts run` dice solver missing | En Linux x86_64/Windows amd64 reinstalar el wheel; en otras plataformas compilar los binarios 2D y configurar `NTS_SOLVERS_DIR` |
| `nts-test` no existe | Es un comando de desarrollo; usar `uv run python -m cli.run_tests` |
| `outputs/` aparece en una ruta inesperada | Definir `NTS_HOME` o ejecutar desde el directorio de trabajo deseado |
