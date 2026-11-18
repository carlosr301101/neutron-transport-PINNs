# Empaquetado y publicación

Checklist para construir wheel/sdist con `uv` y publicar el paquete en
TestPyPI o PyPI.

> Alcance: el paquete de PyPI incluye la CLI, la TUI y el solver 1D en Python.
> Los binarios 2D en C de `solvers/runners/` **no** se incluyen en un wheel de
> Python puro. Quien necesite el flujo 2D debe clonar el repositorio y compilar
> esos binarios.

## 1. Antes del primer release

Revisar `pyproject.toml`:

- `name`, `version`, `description`, `readme` y `requires-python`.
- `license` y un archivo `LICENSE`.
- `authors` / `maintainers`.
- `[project.urls]` (repositorio, issues, documentación).
- `classifiers` y `keywords`.
- `[project.scripts]`: cada comando instalado debe funcionar desde el wheel.
- `[tool.setuptools.packages.find]`: incluir solo paquetes importables.
- `[tool.setuptools.package-data]`: assets que no son Python, como
  `tui/app.tcss`.

Decisiones aplicadas:

1. Licencia: MIT (`LICENSE`).
2. El wheel es Python puro: CLI + TUI + solver 1D. Sin `.c`, `.h` ni binarios
   2D.
3. `tests/` no se empaqueta. `nts-test` y `tests` ya no son console scripts;
   en desarrollo se usa `uv run python -m cli.run_tests`.
4. La versión sale de `tui/_version.py`:

   ```toml
   [project]
   dynamic = ["version"]

   [tool.setuptools.dynamic]
   version = { attr = "tui._version.__version__" }
   ```

4. Confirmar que el nombre sigue libre en PyPI:

   ```bash
   uv run python - <<'PY'
   import urllib.request
   url = "https://pypi.org/pypi/neutron-transport-pinns/json"
   try:
       with urllib.request.urlopen(url, timeout=10) as response:
           print("ya existe:", response.status)
   except Exception as exc:
       print("disponible:", getattr(exc, "code", type(exc).__name__))
   PY
   ```

## 2. Versión y changelog

1. Actualizar la versión en `pyproject.toml` y `tui/__init__.py` (o en la
   fuente dinámica).
2. Actualizar `CHANGELOG.md` y `Changelog_EN.md`.
3. Correr la suite:

   ```bash
   uv run python -m cli.run_tests
   ```

4. Commit y tag solo cuando el build de release pase.

## 3. Build

```bash
uv build --clear
```

Los artefactos quedan en `dist/`:

```text
dist/neutron_transport_pinns-<version>.tar.gz
dist/neutron_transport_pinns-<version>-py3-none-any.whl
```

`dist/` ya está en `.gitignore`.

Validar metadata:

```bash
uvx twine check dist/*
```

Inspeccionar el wheel:

```bash
uv run python - <<'PY'
import glob
import zipfile

wheel = glob.glob("dist/*.whl")[0]
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()

print(wheel)
print(len(names), "archivos")
assert any(name.endswith("tui/app.tcss") for name in names), names
print("tui/app.tcss está empaquetado")
PY
```

## 4. Smoke test en entorno limpio

```bash
uv venv /tmp/nts-wheel
uv pip install --python /tmp/nts-wheel/bin/python dist/*.whl

/tmp/nts-wheel/bin/nts --help
/tmp/nts-wheel/bin/nts-1d-run --help
/tmp/nts-wheel/bin/nts-tui     # abrir y salir con q
```

Comprobar el CSS empaquetado:

```bash
/tmp/nts-wheel/bin/python - <<'PY'
from importlib.resources import files
path = files("tui").joinpath("app.tcss")
print(path, path.is_file())
PY
```

Probar las formas de instalación de usuario:

```bash
uv tool install neutron-transport-pinns
uvx --from neutron-transport-pinns nts --help
```

## 5. TestPyPI

Usar un token de TestPyPI:

```bash
UV_PUBLISH_TOKEN=pypi-... \
uv publish \
  --publish-url https://test.pypi.org/legacy/ \
  dist/*
```

Instalar la versión publicada en un entorno limpio:

```bash
uv venv /tmp/nts-testpypi
uv pip install --python /tmp/nts-testpypi/bin/python \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  neutron-transport-pinns==<version>

/tmp/nts-testpypi/bin/nts --help
```

## 6. Workflows de CI y release

`.github/workflows/ci.yml` corre en Linux:

- `uv sync --frozen --extra images`
- `uv run python -m cli.run_tests`
- `uvx ruff check --select F,E9 .`
- un job separado en Ubuntu ejecuta `uv build` y `twine check`

`.github/workflows/release.yml` corre con tags `v*` y publica con trusted
publishing de PyPI (`id-token: write`, environment `pypi`). También verifica
que el tag coincida con `tui/_version.py`.

Configurar el pending publisher en PyPI antes del primer tag:

```text
Project name: neutron-transport-pinns
Owner:        carlosr301101
Repository:   neutron-transport-PINNs
Workflow:     release.yml
Environment:  pypi
```

Crear el environment `pypi` en GitHub Actions y subir un tag:

```bash
git tag -a v3.9.4 -m "neutron-transport-pinns 3.9.4"
git push origin main --tags
```

No se necesita el secreto `PYPI_TOKEN` para este camino.

## 7. PyPI

Primero un dry run:

```bash
uv publish --dry-run
```

Camino recomendado: dejar que `release.yml` publique desde un tag `v*` con
trusted publishing. Solo como fallback manual:

```bash
UV_PUBLISH_TOKEN=pypi-... uv publish
```

Con GitHub Actions, conceder `id-token: write` y usar un environment protegido
por un trusted publisher de PyPI. El token es un fallback, no el camino
recomendado.

Evitar subidas duplicadas:

```bash
uv publish \
  --check-url https://pypi.org/simple/neutron-transport-pinns/ \
  dist/*
```

## 8. Release

Guía paso a paso de versión, tag y workflow: [RELEASING.md](RELEASING.md).


```bash
git tag -a v<version> -m "neutron-transport-pinns <version>"
git push origin main --tags
```

Crear las notas de release desde `CHANGELOG.md`.

## 9. Troubleshooting

| Síntoma | Solución |
|---|---|
| `twine check` se queja de metadata | Agregar `license`, `authors`, `urls` y classifiers |
| Falta `tui/app.tcss` en el wheel | Revisar `[tool.setuptools.package-data]` |
| `nts-test` falla desde el wheel | Fue eliminado; usar `uv run python -m cli.run_tests` en el repo |
| `nts run` dice solver missing | Los binarios 2D no van en el wheel; compilarlos desde el repo |
| TestPyPI no encuentra dependencias | Agregar `--extra-index-url https://pypi.org/simple/` |
| La versión ya existe | Subir la versión; PyPI no permite reemplazar archivos |
| `uv publish` no autentica | Configurar `UV_PUBLISH_TOKEN` o trusted publishing |
