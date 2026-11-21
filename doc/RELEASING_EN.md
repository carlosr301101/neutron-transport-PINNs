# Publish a new version

Workflow for bumping the version, creating a GitHub tag, and letting
`.github/workflows/release.yml` publish to PyPI with trusted publishing.

## Summary

```text
version bump -> tests -> build -> commit -> push main -> tag vX.Y.Z
-> GitHub Actions -> PyPI
```

The workflow triggers only on `v*` tags. Before publishing it runs the full
`ci.yml`: if the Ubuntu or Windows tests fail, `publish` does not run.

## 0. Before you start

Check once:

- PyPI trusted publisher configured for:
  - project `neutron-transport-pinns`
  - owner `carlosr301101`
  - repo `neutron-transport-PINNs`
  - workflow `release.yml`
  - environment `pypi`
- `pypi` environment created in GitHub.
- `v*` tags protected with a ruleset.
- `main` clean and up to date.

```bash
git switch main
git pull origin main
git status --short
```

There must be no uncommitted changes.

## 1. Choose the version

Use SemVer:

```text
3.10.0 -> 3.10.1   fix
3.10.0 -> 3.11.0  feature
3.10.0 -> 4.0.0   breaking change
```

Never reuse a version already published on PyPI.

## 2. Bump the version

The single source is:

```text
tui/_version.py
```

Edit:

```python
__version__ = "3.10.1"
```

Do not edit `version` in `pyproject.toml`; it is dynamic:

```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = { attr = "tui._version.__version__" }
```

## 3. Update the changelog

Add the section at the top of:

- `CHANGELOG.md`
- `Changelog_EN.md`

Example:

```markdown
## [3.10.1] - 2026-11-18 - Short title

### Fixed
- Change description.
```

## 4. Update version references

Review and update if present:

- version badge in `README.md`;
- version in `skills/nts-pinns-autopilot/SKILL.md`;
- examples pinned to a version.

## 5. Local verification

```bash
uv run python -m cli.run_tests
uvx ruff check --select F,E9 .
uv build --clear
uvx twine check dist/*
```

Inspect the wheel:

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

It must include `tui/app.tcss` and exclude tests and C files.

Optional smoke test:

```bash
uv venv /tmp/nts-release
uv pip install --python /tmp/nts-release/bin/python dist/*.whl
/tmp/nts-release/bin/nts --help
/tmp/nts-release/bin/nts-tui
```

## 6. Commit

```bash
git add tui/_version.py CHANGELOG.md Changelog_EN.md README.md
git commit -m "chore(release): v3.10.1"
```

Add other files if the release includes code or docs changes.

## 7. Push to main

```bash
git push origin main
```

Wait for CI to pass on GitHub Actions.

## 8. Create and push the tag

The tag must match `tui/_version.py` exactly.

```bash
git tag -a v3.10.1 -m "neutron-transport-pinns 3.10.1"
git push origin v3.10.1
```

Alternatively:

```bash
git push origin main --tags
```

Pushing only the new tag is safer.

## 9. What `release.yml` does

On `v3.10.1`:

1. Runs CI on Ubuntu and Windows (`ci.yml`), including the `cp1252` console
   test.
2. If both pass, checks `v3.10.1 == tui/_version.py`.
3. Runs `uv build --clear`.
4. Runs `uvx twine check dist/*`.
5. Publishes with:

```bash
uv publish --trusted-publishing automatic
```

If any CI job fails, `publish` does not run.

It does not use `PYPI_TOKEN`.

Watch it here:

```text
GitHub → Actions → Release
```

If the `pypi` environment has required reviewers, the job waits for approval.
Otherwise it publishes automatically.

## 10. Create the GitHub Release

After the tag exists:

```text
GitHub → Releases → Draft a new release
```

- Tag: `v3.10.1`
- Title: `neutron-transport-pinns 3.10.1`
- Description: copy the changelog section.
- Publish release.

The GitHub Release is informational; `release.yml` already published to PyPI
from the tag.

## 11. Verify PyPI

```text
https://pypi.org/project/neutron-transport-pinns/3.10.1/
```

Clean install:

```bash
uv venv /tmp/nts-pypi
uv pip install --python /tmp/nts-pypi/bin/python \
  neutron-transport-pinns==3.10.1

/tmp/nts-pypi/bin/python -c "import tui; print(tui.__version__)"
/tmp/nts-pypi/bin/nts --help
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Workflow does not trigger | Tag must start with `v` and match `v*` |
| `Check tag matches package version` fails | Tag and `tui/_version.py` differ |
| Job waits for approval | Approve the `pypi` environment deployment |
| Trusted publishing fails | Check owner/repo/workflow/environment in PyPI |
| `File already exists` | That version is already on PyPI; publish another version |
| Version missing on PyPI | Check the Release job log |
| Wrong version published | It cannot be replaced; publish a new patch |

## Checklist

```text
[ ] Version chosen
[ ] tui/_version.py updated
[ ] CHANGELOG.md and Changelog_EN.md updated
[ ] Tests pass
[ ] uv build passes
[ ] twine check passes
[ ] chore(release) commit created
[ ] main pushed
[ ] vX.Y.Z tag created and pushed
[ ] Release workflow green
[ ] PyPI shows the version
[ ] GitHub Release published
```
