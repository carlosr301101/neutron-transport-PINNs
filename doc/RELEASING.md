# Publicar una nueva versión

Flujo para aumentar la versión, crear el tag en GitHub y dejar que
`.github/workflows/release.yml` publique en PyPI con trusted publishing.

## Resumen

```text
cambio de versión -> tests -> build -> commit -> push main -> tag vX.Y.Z
-> GitHub Actions -> PyPI
```

El workflow se dispara únicamente con tags `v*`. Antes de publicar ejecuta
`ci.yml` completo: si los tests de Ubuntu o Windows fallan, `publish` no corre.

Cada release genera tres archivos en PyPI:

```text
neutron_transport_pinns-<version>-py3-none-manylinux_2_28_x86_64.whl
neutron_transport_pinns-<version>-py3-none-win_amd64.whl
neutron_transport_pinns-<version>.tar.gz
```

## 0. Antes de empezar

Verificar una sola vez:

- PyPI trusted publisher configurado para:
  - proyecto `neutron-transport-pinns`
  - owner `carlosr301101`
  - repo `neutron-transport-PINNs`
  - workflow `release.yml`
  - environment `pypi`
- Environment `pypi` creado en GitHub.
- Tags `v*` protegidos con un ruleset.
- `main` limpio y actualizado.

```bash
git switch main
git pull origin main
git status --short
```

No debe haber cambios sin commitear.

## 1. Elegir la versión

Usar SemVer:

```text
4.0.0 -> 4.0.1   fix
4.0.0 -> 4.1.0   feature
4.0.0 -> 5.0.0   cambio incompatible
```

No reutilizar una versión ya publicada en PyPI.

## 2. Cambiar la versión

La única fuente es:

```text
tui/_version.py
```

Editar:

```python
__version__ = "4.0.0"
```

No editar `version` en `pyproject.toml`; es dinámico:

```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = { attr = "tui._version.__version__" }
```

## 3. Actualizar changelog

Añadir la sección al inicio de:

- `CHANGELOG.md`
- `Changelog_EN.md`

Ejemplo:

```markdown
## [4.0.0] - 2026-11-24 - Flujo 2D y wheels por plataforma

### Fixed
- Descripción del cambio.
```

## 4. Actualizar referencias de versión

Revisar y actualizar si aparecen:

- badge de versión en `README.md`;
- versión en `skills/nts-pinns-autopilot/SKILL.md`;
- ejemplos con versión fija.

## 5. Verificación local

```bash
uv run python -m cli.run_tests
uvx ruff check --select F,E9 .
```

Construir los artefactos igual que el release:

```bash
# Linux (dentro de manylinux_2_28) o local para un wheel linux_x86_64
make -C solvers
NTS_WHEEL_PLATFORM=manylinux_2_28_x86_64 uv build --wheel --out-dir dist

# Windows
# .\solvers\build_windows.ps1
# $env:NTS_WHEEL_PLATFORM = "win_amd64"; uv build --wheel --out-dir dist

uv build --sdist --out-dir dist
uvx twine check dist/*
```

Comprobar los artefactos:

```bash
uv run python - <<'PY'
import glob, stat, tarfile, zipfile

wheel = glob.glob("dist/*manylinux*.whl")[0]
with zipfile.ZipFile(wheel) as archive:
    infos = {info.filename: info for info in archive.infolist()}

print(wheel)
for name in ("NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN"):
    mode = infos[f"solvers/runners/{name}"].external_attr >> 16
    assert mode & stat.S_IXUSR, name
assert "tui/app.tcss" in infos and "tui2d/app.tcss" in infos
assert "templates/base_input.json" in infos
assert not any(name.endswith(".c") for name in infos)

sdist = glob.glob("dist/*.tar.gz")[0]
with tarfile.open(sdist) as archive:
    names = archive.getnames()
assert any(name.endswith("NTS_DD.c") for name in names)
assert any(name.endswith("solvers/Makefile") for name in names)
assert not any(name.endswith("/solvers/runners/NTS_DD") for name in names)
print("wheel y sdist OK")
PY
```

Smoke test opcional:

```bash
uv venv /tmp/nts-release --python 3.14
uv pip install --python /tmp/nts-release/bin/python dist/*manylinux*.whl
/tmp/nts-release/bin/nts status        # cinco OK
/tmp/nts-release/bin/python -c "import tui2d.app; print('TUI 2D OK')"
```

## 6. Commit

```bash
git add tui/_version.py CHANGELOG.md Changelog_EN.md README.md
git commit -m "chore(release): 4.0.0"
```

Añadir otros archivos si el release incluye cambios de código o docs.

## 7. Push a main

```bash
git push origin main
```

Esperar a que CI pase en GitHub Actions.

## 8. Crear y subir el tag

El tag debe coincidir exactamente con `tui/_version.py`.

```bash
git tag -s v4.0.0 -m "neutron-transport-pinns 4.0.0"
git push origin v4.0.0
```

También vale:

```bash
git push origin main --tags
```

Pero es más seguro subir solo el tag nuevo.

## 9. Qué hace `release.yml`

Al subir `v4.0.0`:

1. Ejecuta CI en Ubuntu y Windows (`ci.yml`), incluida la compilación de
   solvers, la prueba de consola `cp1252` y los smoke tests de wheel.
2. Si todo pasa, verifica `v4.0.0 == tui/_version.py`.
3. Construye el wheel manylinux en `quay.io/pypa/manylinux_2_28_x86_64`.
4. Construye el wheel `win_amd64` con MSYS2/UCRT64 y `-static`.
5. Prueba ambos wheels (`nts status` y una corrida 2D).
6. Construye el sdist (fuentes C, sin binarios).
7. Ejecuta `uvx twine check dist/*`.
8. Publica los tres archivos con:

```bash
uv publish --trusted-publishing automatic
```

Si cualquier job de CI falla, `publish` no se ejecuta.

No usa `PYPI_TOKEN`.

Ver el progreso:

```text
GitHub → Actions → Release
```

Si el environment `pypi` tiene required reviewers, el job queda esperando
aprobación. Si no, publica automáticamente.

## 10. Crear el GitHub Release

Después de que el tag exista:

```text
GitHub → Releases → Draft a new release
```

- Tag: `v4.0.0`
- Título: `neutron-transport-pinns 4.0.0`
- Descripción: copiar la sección del changelog.
- Publish release.

El Release de GitHub es informativo; la publicación en PyPI ya la hace
`release.yml` con el tag.

## 11. Verificar PyPI

```text
https://pypi.org/project/neutron-transport-pinns/4.0.0/
```

Instalación limpia:

```bash
uv venv /tmp/nts-pypi
uv pip install --python /tmp/nts-pypi/bin/python \
  neutron-transport-pinns==4.0.0

/tmp/nts-pypi/bin/python -c "import tui; print(tui.__version__)"
/tmp/nts-pypi/bin/nts --help
/tmp/nts-pypi/bin/nts status    # cinco solvers OK en Linux/Windows x86_64
/tmp/nts-pypi/bin/python -c "import tui2d.app; print('TUI 2D OK')"
```

## Troubleshooting

| Problema | Solución |
|---|---|
| El workflow no se dispara | El tag debe empezar con `v` y coincidir con `v*` |
| `Check tag matches package version` falla | El tag y `tui/_version.py` no coinciden |
| El job espera aprobación | Aprobar en el environment `pypi` |
| `Trusted publishing` falla | Revisar owner/repo/workflow/environment en PyPI |
| `File already exists` | Esa versión ya está en PyPI; subir otra versión |
| PyPI no muestra la versión | Revisar el log del job Release |
| Se publicó una versión equivocada | No se puede reemplazar; publicar un patch nuevo |

## Checklist

```text
[ ] Versión elegida
[ ] tui/_version.py actualizado
[ ] CHANGELOG.md y Changelog_EN.md actualizados
[ ] Tests OK
[ ] uv build OK
[ ] twine check OK
[ ] Commit chore(release) creado
[ ] main pusheado
[ ] Tag vX.Y.Z creado y pusheado
[ ] Workflow Release verde
[ ] PyPI muestra la versión
[ ] GitHub Release publicado
```
