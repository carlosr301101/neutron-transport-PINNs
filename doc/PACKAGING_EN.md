# Packaging and publishing

Checklist for building the platform wheels and the sdist with `uv` and
publishing the package to TestPyPI or PyPI.

> Scope: the **Linux x86_64** and **Windows amd64** wheels contain the CLI, both
> TUIs, the Python 1D solver and the five 2D C binaries. The sdist contains the
> C sources and build helpers, but no binaries. macOS, ARM and other platforms
> install the sdist and compile the solvers themselves.

## 1. Before the first release

Review `pyproject.toml` and `setup.py`:

- `name`, `version`, `description`, `readme` and `requires-python`.
- `license` and a `LICENSE` file.
- `authors` / `maintainers`.
- `[project.urls]` (repository, issues, documentation).
- `classifiers` and `keywords`.
- `[project.scripts]`: every installed command must work from a wheel.
- `[tool.setuptools.packages.find]`: `cli`, `core`, `execution`, `utils`,
  `tui*`, `tui2d*`, `solvers*`, `templates`.
- `setup.py`: platform binaries, `package_data` and the wheel tag.

Applied decisions:

1. License: MIT (`LICENSE`).
2. The wheel is **platform-specific** because it carries native executables.
3. Linux wheel: `py3-none-manylinux_2_28_x86_64`.
4. Windows wheel: `py3-none-win_amd64`.
5. `NTS_WHEEL_PLATFORM` overrides the platform tag during the build.
6. Editable installs (`uv sync`, `pip install -e`) stay `py3-none-any`; this
   avoids a uv wheel-variant mismatch.
7. `tests/` is not packaged. `nts-test` is development-only.
8. The version comes from `tui/_version.py`:

   ```toml
   [project]
   dynamic = ["version"]

   [tool.setuptools.dynamic]
   version = { attr = "tui._version.__version__" }
   ```

## 2. Build the Linux wheel

Compile the binaries first and build inside a `manylinux_2_28` container so the
glibc baseline matches the tag:

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

## 3. Build the Windows wheel

From an **MSYS2 UCRT64** shell (`gcc` on `PATH`):

```powershell
pwsh -File solvers/build_windows.ps1
# or point at the compiler explicitly
pwsh -File solvers/build_windows.ps1 -Gcc (cygpath -w (which gcc))

$env:NTS_WHEEL_PLATFORM = "win_amd64"
uv build --wheel --out-dir dist
```

`build_windows.ps1` also accepts a Windows path such as
`-Gcc "C:\msys64\ucrt64\bin\gcc.exe"` and falls back to `MSYS2_LOCATION` or the
standard `C:\msys64` installation when `-Gcc` is omitted. The `.exe` files are
linked with `-static`, so they do not need MinGW DLLs.

## 4. Build the sdist

```bash
uv build --sdist --out-dir dist
```

Artifacts:

```text
dist/neutron_transport_pinns-<version>-py3-none-manylinux_2_28_x86_64.whl
dist/neutron_transport_pinns-<version>-py3-none-win_amd64.whl
dist/neutron_transport_pinns-<version>.tar.gz
```

`dist/` is already in `.gitignore`.

Validate metadata:

```bash
uvx twine check dist/*
```

## 5. Inspect the artifacts

Wheel: binaries with the executable bit, both stylesheets and no C sources:

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

For the Windows wheel, check `solvers/runners/NTS_*.exe` instead.

Sdist: sources and helpers included, binaries excluded:

```bash
tar tzf dist/*.tar.gz | grep -E "NTS_.*\.c|Makefile|build_windows|base_input"
tar tzf dist/*.tar.gz | grep -E "NTS_(DD|LD|STEP|RM_CN|RM_LLN)$" && exit 1 || true
```

## 6. Clean-install smoke test

Linux:

```bash
uv venv /tmp/nts-wheel --python 3.14
uv pip install --python /tmp/nts-wheel/bin/python dist/*manylinux*.whl
export NTS_HOME=/tmp/nts-home
mkdir -p "$NTS_HOME"
/tmp/nts-wheel/bin/nts status        # five OK
printf '4\n1\n0.5 0.3\n1\n10.0 4\n1\n10.0 4\n1\n1.0\n0.0 0.0 0.0 0.0\n1e-4\n' > "$NTS_HOME/input.txt"
/tmp/nts-wheel/bin/nts run -s NTS_DD -i "$NTS_HOME/input.txt"
/tmp/nts-wheel/bin/python -c "import tui2d.app; print('TUI 2D OK')"
```

Check the packaged assets:

```bash
/tmp/nts-wheel/bin/python - <<'PY'
from importlib.resources import files
print(files("tui").joinpath("app.tcss").is_file())
print(files("tui2d").joinpath("app.tcss").is_file())
print(files("templates").joinpath("base_input.json").is_file())
PY
```

Windows: repeat with a venv and `nts.exe`.

## 7. CI and release workflows

`.github/workflows/ci.yml`:

- Runs on branch pushes and pull requests, **not** on tags.
- Ubuntu and Windows compile the 2D solvers and run the test suite.
- A `build` matrix builds the platform wheel for each OS, installs it in a
  clean venv, runs `nts status` and executes a 2D case.
- Linux also builds the sdist and runs `twine check`.
- When Release calls it (`workflow_call` with `run_build: false`), the `build`
  job is skipped, so there are no duplicate smoke wheels or artifacts.

`.github/workflows/release.yml`, on `v*` tags:

1. Runs the CI tests once (no separate push CI).
2. Builds the manylinux wheel in `quay.io/pypa/manylinux_2_28_x86_64` and
   rejects the build if the tag is not `manylinux_2_28_x86_64`.
3. Builds the `win_amd64` wheel with MSYS2/UCRT64 and `-static`, and rejects the
   build if the tag is not `win_amd64`.
4. Smoke-tests both wheels (`nts status` + `nts run`).
5. Builds the sdist.
6. Downloads only `wheel-linux`, `wheel-windows` and `sdist`, verifies that
   there are exactly three files, checks the tag against `tui/_version.py`,
   runs `twine check` and publishes with trusted publishing.

Configure the pending publisher in PyPI before the first tag:

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

Install the published version in a clean environment:

```bash
uv venv /tmp/nts-testpypi --python 3.14
uv pip install --python /tmp/nts-testpypi/bin/python \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  neutron-transport-pinns==<version>
/tmp/nts-testpypi/bin/nts status
```

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `twine check` complains about metadata | Add `license`, `authors`, `urls` and classifiers |
| `tui/app.tcss` or `tui2d/app.tcss` missing | Check `setup.py` `package_data` |
| Binaries missing from the wheel | Compile them before building; check `setup.py` suffix (`.exe` on Windows) |
| Wheel has an ABI tag (`cp314-cp314-...`) | The custom `bdist_wheel.get_tag()` was not applied |
| `uv sync` fails with `variant.json` | Editable builds must stay `py3-none-any`; see `setup.py` |
| `nts run` says solver missing | On Linux/Windows x86_64 reinstall the wheel; otherwise compile and set `NTS_SOLVERS_DIR` |
| Binary installed without execute permission | Verify with `stat`; reinstall with a recent pip/uv |
| `File already exists` on PyPI | Bump the version; PyPI does not allow replacing files |

## 10. Release

Step-by-step version bump, tag and workflow guide:
[RELEASING_EN.md](RELEASING_EN.md).
