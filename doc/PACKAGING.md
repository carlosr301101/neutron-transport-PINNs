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

Problemas conocidos a resolver antes de publicar:

1. `nts-test` y `tests` son entry points, pero `tests/` no se empaqueta.
   Quitarlos del wheel o empaquetar los tests de forma intencional.
2. Si no se distribuyen los binarios 2D, documentar que desde PyPI solo está
   disponible el flujo 1D/TUI.
3. Mantener una sola fuente de versión. Opción A: versión estática en
   `pyproject.toml`. Opción B: versión dinámica:

   ```toml
   [project]
   dynamic = ["version"]

   [tool.setuptools.dynamic]
   version = { attr = "tui.__version__" }
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
   uv run nts-test
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

## 6. PyPI

Primero un dry run:

```bash
uv publish --dry-run
```

Publicar con token:

```bash
UV_PUBLISH_TOKEN=pypi-... uv publish
```

O usar trusted publishing desde CI:

```bash
uv publish --trusted-publishing automatic
```

Con GitHub Actions, conceder `id-token: write` y usar un environment protegido
por un trusted publisher de PyPI.

Evitar subidas duplicadas:

```bash
uv publish \
  --check-url https://pypi.org/simple/neutron-transport-pinns/ \
  dist/*
```

## 7. Release

```bash
git tag -a v<version> -m "neutron-transport-pinns <version>"
git push origin main --tags
```

Crear las notas de release desde `CHANGELOG.md`.

## 8. Troubleshooting

| Síntoma | Solución |
|---|---|
| `twine check` se queja de metadata | Agregar `license`, `authors`, `urls` y classifiers |
| Falta `tui/app.tcss` en el wheel | Revisar `[tool.setuptools.package-data]` |
| `nts-test` falla desde el wheel | Es un comando solo del repo; quitarlo del wheel o empaquetar tests |
| `nts run` dice solver missing | Los binarios 2D no van en el wheel; compilarlos desde el repo |
| TestPyPI no encuentra dependencias | Agregar `--extra-index-url https://pypi.org/simple/` |
| La versión ya existe | Subir la versión; PyPI no permite reemplazar archivos |
| `uv publish` no autentica | Configurar `UV_PUBLISH_TOKEN` o trusted publishing |
