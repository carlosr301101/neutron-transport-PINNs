# Packaging and publishing

Checklist for building a wheel/sdist with `uv` and publishing the package to
TestPyPI or PyPI.

> Scope: the PyPI package contains the CLI, the TUI and the Python 1D solver.
> The 2D C binaries in `solvers/runners/` are **not** included in a pure-Python
> wheel. Users who need the 2D workflow must clone the repository and compile
> those binaries.

## 1. Before the first release

Review `pyproject.toml`:

- `name`, `version`, `description`, `readme` and `requires-python`.
- `license` and a `LICENSE` file.
- `authors` / `maintainers`.
- `[project.urls]` (repository, issues, documentation).
- `classifiers` and `keywords`.
- `[project.scripts]`: every installed command must work from a wheel.
- `[tool.setuptools.packages.find]`: include only importable packages.
- `[tool.setuptools.package-data]`: non-Python assets such as
  `tui/app.tcss`.

Applied decisions:

1. License: MIT (`LICENSE`).
2. The wheel is Python-only: CLI + TUI + 1D solver. No `.c`, `.h` or 2D
   binaries.
3. `tests/` is not packaged. `nts-test` and `tests` are not console scripts;
   development uses `uv run python -m cli.run_tests`.
4. The version comes from `tui/_version.py`:

   ```toml
   [project]
   dynamic = ["version"]

   [tool.setuptools.dynamic]
   version = { attr = "tui._version.__version__" }
   ```

4. Confirm the package name is still available on PyPI:

   ```bash
   uv run python - <<'PY'
   import urllib.request
   url = "https://pypi.org/pypi/neutron-transport-pinns/json"
   try:
       with urllib.request.urlopen(url, timeout=10) as response:
           print("already exists:", response.status)
   except Exception as exc:
       print("available:", getattr(exc, "code", type(exc).__name__))
   PY
   ```

## 2. Version and changelog

1. Update the version in `pyproject.toml` and `tui/__init__.py` (or the dynamic
   source).
2. Update `CHANGELOG.md` and `Changelog_EN.md`.
3. Run the suite:

   ```bash
   uv run python -m cli.run_tests
   ```

4. Commit and tag only after the release build passes.

## 3. Build

```bash
uv build --clear
```

The artifacts are written to `dist/`:

```text
dist/neutron_transport_pinns-<version>.tar.gz
dist/neutron_transport_pinns-<version>-py3-none-any.whl
```

`dist/` is already in `.gitignore`.

Validate the metadata:

```bash
uvx twine check dist/*
```

Inspect the wheel:

```bash
uv run python - <<'PY'
import glob
import zipfile

wheel = glob.glob("dist/*.whl")[0]
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()

print(wheel)
print(len(names), "files")
assert any(name.endswith("tui/app.tcss") for name in names), names
print("tui/app.tcss is packaged")
PY
```

## 4. Clean-install smoke test

```bash
uv venv /tmp/nts-wheel
uv pip install --python /tmp/nts-wheel/bin/python dist/*.whl

/tmp/nts-wheel/bin/nts --help
/tmp/nts-wheel/bin/nts-1d-run --help
/tmp/nts-wheel/bin/nts-tui     # open and quit with q
```

Check the packaged CSS:

```bash
/tmp/nts-wheel/bin/python - <<'PY'
from importlib.resources import files
path = files("tui").joinpath("app.tcss")
print(path, path.is_file())
PY
```

Test the end-user install paths:

```bash
uv tool install neutron-transport-pinns
uvx --from neutron-transport-pinns nts --help
```

## 5. TestPyPI

Use a TestPyPI token:

```bash
UV_PUBLISH_TOKEN=pypi-... \
uv publish \
  --publish-url https://test.pypi.org/legacy/ \
  dist/*
```

Install the published version in a clean environment:

```bash
uv venv /tmp/nts-testpypi
uv pip install --python /tmp/nts-testpypi/bin/python \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  neutron-transport-pinns==<version>

/tmp/nts-testpypi/bin/nts --help
```

## 6. CI and release workflows

`.github/workflows/ci.yml` runs on Linux and Windows:

- `uv sync --frozen --extra images`
- `uv run python -m cli.run_tests`
- `uvx ruff check --select F,E9 .`
- a separate Ubuntu job runs `uv build` and `twine check`

`.github/workflows/release.yml` runs on `v*` tags and publishes with PyPI
trusted publishing (`id-token: write`, environment `pypi`). It also checks that
the tag matches `tui/_version.py`.

Configure the pending publisher in PyPI before the first tag:

```text
Project name: neutron-transport-pinns
Owner:        carlosr301101
Repository:   neutron-transport-PINNs
Workflow:     release.yml
Environment:  pypi
```

Create the `pypi` environment in GitHub Actions, then push a tag:

```bash
git tag -a v3.9.2 -m "neutron-transport-pinns 3.9.2"
git push origin main --tags
```

No `PYPI_TOKEN` secret is needed for this path.

## 7. PyPI

Dry run first:

```bash
uv publish --dry-run
```

Preferred path: let the `release.yml` workflow publish from a `v*` tag using
trusted publishing. For a manual fallback only:

```bash
UV_PUBLISH_TOKEN=pypi-... uv publish
```

With GitHub Actions, grant `id-token: write` and use an environment protected
by a PyPI trusted publisher. The token path is a fallback, not the recommended
release path.

Avoid duplicate uploads:

```bash
uv publish \
  --check-url https://pypi.org/simple/neutron-transport-pinns/ \
  dist/*
```

## 8. Release

```bash
git tag -a v<version> -m "neutron-transport-pinns <version>"
git push origin main --tags
```

Create the release notes from `CHANGELOG.md`.

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `twine check` complains about metadata | Add `license`, `authors`, `urls` and classifiers |
| `tui/app.tcss` missing from wheel | Check `[tool.setuptools.package-data]` |
| `nts-test` fails from wheel | It was removed; use `uv run python -m cli.run_tests` in the repo |
| `nts run` says solver missing | The 2D binaries are not in the wheel; compile them from the repo |
| TestPyPI install cannot find dependencies | Add `--extra-index-url https://pypi.org/simple/` |
| Version already exists | Bump the version; PyPI does not allow replacing files |
| `uv publish` cannot authenticate | Set `UV_PUBLISH_TOKEN` or configure trusted publishing |
