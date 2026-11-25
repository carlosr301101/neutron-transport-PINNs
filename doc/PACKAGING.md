# Empaquetado y publicación

Checklist para construir los wheels por plataforma y el sdist con `uv`, y
publicar el paquete en TestPyPI o PyPI.

> Alcance: los wheels de **Linux x86_64** y **Windows amd64** incluyen la CLI,
> las dos TUI, el solver 1D en Python y los cinco binarios 2D. El sdist incluye
> las fuentes C y los scripts de build, pero no los binarios. macOS, ARM y otras
> plataformas instalan el sdist y compilan los solvers.

## 1. Antes del primer release

Revisar `pyproject.toml` y `setup.py`:

- `name`, `version`, `description`, `readme` y `requires-python`.
- `license` y un archivo `LICENSE`.
- `authors` / `maintainers`.
- `[project.urls]` (repositorio, issues, documentación).
- `classifiers` y `keywords`.
- `[project.scripts]`: cada comando instalado debe funcionar desde el wheel.
- `[tool.setuptools.packages.find]`: `cli`, `core`, `execution`, `utils`,
  `tui*`, `tui2d*`, `solvers*`, `templates`.
- `setup.py`: binarios por plataforma, `package_data` y el tag del wheel.

Decisiones aplicadas:

1. Licencia: MIT (`LICENSE`).
2. El wheel es **específico de plataforma** porque lleva ejecutables nativos.
3. Wheel Linux: `py3-none-manylinux_2_28_x86_64`.
4. Wheel Windows: `py3-none-win_amd64`.
5. `NTS_WHEEL_PLATFORM` permite forzar el tag durante el build.
6. Los builds editables (`uv sync`, `pip install -e`) siguen siendo
   `py3-none-any` para evitar el conflicto de variantes de uv.
7. `tests/` no se empaqueta. `nts-test` es solo de desarrollo.
8. La versión sale de `tui/_version.py`:

   ```toml
   [project]
   dynamic = ["version"]

   [tool.setuptools.dynamic]
   version = { attr = "tui._version.__version__" }
   ```

## 2. Construir el wheel de Linux

Compilar los binarios y construir dentro de un contenedor `manylinux_2_28`
para que la base glibc coincida con el tag:

```bash
podman run --rm -v "$PWD:/src:Z" -w /src \
  quay.io/pypa/manylinux_2_28_x86_64 bash -lc '
    make -C solvers CC=gcc
    PY=$(ls -d /opt/python/cp314-cp314/bin/python 2>/dev/null || \
         ls -d /opt/python/cp313-cp313/bin/python | tail -1)
    $PY -m pip install --upgrade build
    NTS_WHEEL_PLATFORM=manylinux_2_28_x86_64 \
      $PY -m build --wheel --outdir dist
  '
```

## 3. Construir el wheel de Windows

Desde un shell **MSYS2 UCRT64** (`gcc` en el `PATH`):

```powershell
pwsh -File solvers/build_windows.ps1
# o indicar el compilador explícitamente
pwsh -File solvers/build_windows.ps1 -Gcc (cygpath -w (which gcc))

$env:NTS_WHEEL_PLATFORM = "win_amd64"
uv build --wheel --out-dir dist
```

`build_windows.ps1` también acepta una ruta Windows como
`-Gcc "C:\msys64\ucrt64\bin\gcc.exe"` y, si se omite `-Gcc`, busca en
`MSYS2_LOCATION` o en la instalación estándar `C:\msys64`. Los `.exe` se
enlazan con `-static`, sin DLLs de MinGW.

## 4. Construir el sdist

```bash
uv build --sdist --out-dir dist
```

Artefactos:

```text
dist/neutron_transport_pinns-<version>-py3-none-manylinux_2_28_x86_64.whl
dist/neutron_transport_pinns-<version>-py3-none-win_amd64.whl
dist/neutron_transport_pinns-<version>.tar.gz
```

`dist/` ya está en `.gitignore`.

Validar metadatos:

```bash
uvx twine check dist/*
```

## 5. Inspeccionar los artefactos

Wheel: binarios con permiso de ejecución, ambos estilos y sin fuentes C:

```bash
uv run python - <<'PY'
import glob, stat, zipfile

wheel = glob.glob("dist/*manylinux*.whl")[0]
with zipfile.ZipFile(wheel) as archive:
    infos = {info.filename: info for info in archive.infolist()}

print(wheel)
for name in ("NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN"):
    info = infos[f"solvers/runners/{name}"]
    mode = info.external_attr >> 16
    assert mode & stat.S_IXUSR, name
    print(name, oct(mode))
assert "tui/app.tcss" in infos
assert "tui2d/app.tcss" in infos
assert "templates/base_input.json" in infos
assert not any(name.endswith(".c") for name in infos)
PY
```

Para el wheel de Windows, comprobar `solvers/runners/NTS_*.exe`.

Sdist: fuentes y scripts incluidos, binarios fuera:

```bash
tar tzf dist/*.tar.gz | grep -E "NTS_.*\.c|Makefile|build_windows|base_input"
tar tzf dist/*.tar.gz | grep -E "NTS_(DD|LD|STEP|RM_CN|RM_LLN)$" && exit 1 || true
```

## 6. Prueba en venv limpia

Linux:

```bash
uv venv /tmp/nts-wheel --python 3.14
uv pip install --python /tmp/nts-wheel/bin/python dist/*manylinux*.whl
export NTS_HOME=/tmp/nts-home
mkdir -p "$NTS_HOME"
/tmp/nts-wheel/bin/nts status        # cinco OK
printf '4\n1\n0.5 0.3\n1\n10.0 4\n1\n10.0 4\n1\n1.0\n0.0 0.0 0.0 0.0\n1e-4\n' > "$NTS_HOME/input.txt"
/tmp/nts-wheel/bin/nts run -s NTS_DD -i "$NTS_HOME/input.txt"
/tmp/nts-wheel/bin/python -c "import tui2d.app; print('TUI 2D OK')"
```

Comprobar los assets empaquetados:

```bash
/tmp/nts-wheel/bin/python - <<'PY'
from importlib.resources import files
print(files("tui").joinpath("app.tcss").is_file())
print(files("tui2d").joinpath("app.tcss").is_file())
print(files("templates").joinpath("base_input.json").is_file())
PY
```

En Windows, repetir con una venv y `nts.exe`.

## 7. CI y workflows de release

`.github/workflows/ci.yml`:

- Se ejecuta con pushes de ramas y pull requests, **no** con tags.
- Ubuntu y Windows compilan los solvers 2D y ejecutan los tests.
- Una matriz `build` construye el wheel de cada plataforma, lo instala en una
  venv limpia, ejecuta `nts status` y corre un caso 2D.
- Linux construye además el sdist y ejecuta `twine check`.
- Cuando lo llama Release (`workflow_call` con `run_build: false`), el job
  `build` se omite: no hay wheels de humo ni artefactos duplicados.

`.github/workflows/release.yml`, con tags `v*`:

1. Ejecuta los tests una sola vez (no hay CI suelto en el tag).
2. Construye el wheel manylinux en `quay.io/pypa/manylinux_2_28_x86_64` y falla
   si el tag no es `manylinux_2_28_x86_64`.
3. Construye el wheel `win_amd64` con MSYS2/UCRT64 y `-static`, y falla si el
   tag no es `win_amd64`.
4. Prueba ambos wheels (`nts status` + `nts run`).
5. Construye el sdist.
6. Descarga solo `wheel-linux`, `wheel-windows` y `sdist`, verifica que haya
   exactamente tres archivos, comprueba el tag contra `tui/_version.py`,
   ejecuta `twine check` y publica con trusted publishing.

Configurar el pending publisher en PyPI antes del primer tag:

```text
Project name: neutron-transport-pinns
Owner:        carlosr301101
Repository:   neutron-transport-PINNs
Workflow:     release.yml
Environment:  pypi
```

## 8. TestPyPI

```bash
UV_PUBLISH_TOKEN=pypi-... \
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

Instalar la versión publicada en un entorno limpio:

```bash
uv venv /tmp/nts-testpypi --python 3.14
uv pip install --python /tmp/nts-testpypi/bin/python \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  neutron-transport-pinns==<version>
/tmp/nts-testpypi/bin/nts status
```

## 9. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `twine check` se queja de metadatos | Revisar `license`, `authors`, `urls` y classifiers |
| Falta `tui/app.tcss` o `tui2d/app.tcss` | Revisar `package_data` en `setup.py` |
| Faltan binarios en el wheel | Compilarlos antes del build; revisar el sufijo `.exe` en Windows |
| El wheel sale con ABI (`cp314-cp314-...`) | No se aplicó `bdist_wheel.get_tag()` |
| `uv sync` falla con `variant.json` | Los builds editables deben quedar en `py3-none-any` |
| `nts run` dice solver missing | En Linux/Windows x86_64 reinstalar el wheel; en otras plataformas compilar y usar `NTS_SOLVERS_DIR` |
| Binario sin permiso de ejecución | Comprobar con `stat`; reinstalar con pip/uv reciente |
| `File already exists` en PyPI | Subir otra versión; PyPI no permite reemplazar archivos |

## 10. Release

Guía paso a paso de versión, tag y workflow:
[RELEASING.md](RELEASING.md).
