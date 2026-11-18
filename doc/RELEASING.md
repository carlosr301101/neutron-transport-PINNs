# Publicar una nueva versión

Flujo para aumentar la versión, crear el tag en GitHub y dejar que
`.github/workflows/release.yml` publique en PyPI con trusted publishing.

## Resumen

```text
cambio de versión -> tests -> build -> commit -> push main -> tag vX.Y.Z
-> GitHub Actions -> PyPI
```

El workflow se dispara únicamente con tags `v*`.

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
3.9.4 -> 3.9.5   fix
3.9.4 -> 3.10.0  feature
3.9.4 -> 4.0.0   cambio incompatible
```

No reutilizar una versión ya publicada en PyPI.

## 2. Cambiar la versión

La única fuente es:

```text
tui/_version.py
```

Editar:

```python
__version__ = "3.9.5"
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
## [3.9.5] - 2026-11-18 - Título breve

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
uv build --clear
uvx twine check dist/*
```

Comprobar el wheel:

```bash
uv run python - <<'PY'
import glob, zipfile

wheel = glob.glob("dist/*.whl")[0]
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()

print(wheel)
print("tcss:", [n for n in names if n.endswith(".tcss")])
print("tests:", [n for n in names if n.startswith("tests/")])
print("C:", [n for n in names if n.endswith((".c", ".h"))])
PY
```

Debe incluir `tui/app.tcss` y no incluir tests ni C.

Smoke test opcional:

```bash
uv venv /tmp/nts-release
uv pip install --python /tmp/nts-release/bin/python dist/*.whl
/tmp/nts-release/bin/nts --help
/tmp/nts-release/bin/nts-tui
```

## 6. Commit

```bash
git add tui/_version.py CHANGELOG.md Changelog_EN.md README.md
git commit -m "chore(release): v3.9.5"
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
git tag -a v3.9.5 -m "neutron-transport-pinns 3.9.5"
git push origin v3.9.5
```

También vale:

```bash
git push origin main --tags
```

Pero es más seguro subir solo el tag nuevo.

## 9. Qué hace `release.yml`

Al subir `v3.9.5`:

1. Verifica `v3.9.5 == tui/_version.py`.
2. Ejecuta `uv build --clear`.
3. Ejecuta `uvx twine check dist/*`.
4. Publica con:

```bash
uv publish --trusted-publishing automatic
```

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

- Tag: `v3.9.5`
- Título: `neutron-transport-pinns 3.9.5`
- Descripción: copiar la sección del changelog.
- Publish release.

El Release de GitHub es informativo; la publicación en PyPI ya la hace
`release.yml` con el tag.

## 11. Verificar PyPI

```text
https://pypi.org/project/neutron-transport-pinns/3.9.5/
```

Instalación limpia:

```bash
uv venv /tmp/nts-pypi
uv pip install --python /tmp/nts-pypi/bin/python \
  neutron-transport-pinns==3.9.5

/tmp/nts-pypi/bin/python -c "import tui; print(tui.__version__)"
/tmp/nts-pypi/bin/nts --help
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
