# NTS 2D TUI

Terminal UI for the complete 2D workflow: configuration with a proportional
domain map, runs with the five C solvers, results and MFLUX heatmaps.

> Scope: 2D only. The 1D workflow keeps its own UI in [TUI_EN.md](TUI_EN.md).
>
> Spanish version: [TUI2D.md](TUI2D.md).

## Launch

```bash
uv run nts tui --dim 2
# equivalent
uv run nts-tui-2d
```

`nts tui` (without `--dim`) still opens the 1D UI, so nothing changes for
existing users. `nts tui --dim 2` uses a fast path in `cli/main.py` that skips
the CLI parser.

`nts status` must show the five binaries before running anything:

```text
Solvers:
  OK NTS_DD
  OK NTS_LD
  OK NTS_RM_CN
  OK NTS_RM_LLN
  OK NTS_STEP
```

If they are missing, build them with `make -C solvers` (Linux) or
`solvers/build_windows.ps1` (Windows).

Optional inline heatmap preview:

```bash
uv sync --extra images
```

## Tabs

| Tab | Purpose |
|---|---|
| Dashboard | Version, config/result counts, latest result |
| Config | Zones, X/Y regions, `ZMAP`, `QMAP`, boundary conditions, `N`, `TOL`, solver and `input.txt` preview |
| Run | Select configs, solver and workers; preview, live log, cancel |
| Results | STATUS, ITER, CPU, grid shape and mean flux of each result |
| Plots | MFLUX heatmap with axes in cm |

## Config tab

The form mirrors `nts-2d-config` and produces the JSON consumed by
`nts validate` / `nts generate`.

### Proportional domain map

The top of the Config tab draws the physical domain:

- Width and height follow the sum of the X and Y region lengths in cm.
- Terminal characters are about twice as tall as they are wide, so the
  drawing uses `rows = cols * (Ly / Lx) * 0.5`. A 20 x 10 cm domain is drawn
  twice as wide as tall; a 10 x 20 cm domain is drawn twice as tall as wide.
- Each region is filled with the colour of its zone from `ZMAP`.
- Black `│`, `─` and `┼` lines mark the region boundaries.
- The legend below shows total length, region/cell counts, the drawn aspect,
  the zone palette and the boundary conditions as
  `BC: L=Reflective · B=Vacuum · R=Incoming(2) · T=Vacuum`.

The map updates on every edit of the region tables, `ZMAP` or the BC table.

### Tables and fields

- **Boundary conditions** (directly under the domain map): one row per side
  in the canonical order `left, bottom, right, top`:
  - `Reflective` → `-1.0`
  - `Vacuum` → `0.0`
  - `Incoming flux` → the typed positive value
- **Material zones**: optional `Name`, `Sigma_t`, `Sigma_s`. `Sigma_s` must be
  lower than `Sigma_t`. Names are saved as `ZONE_NAMES`; fill all of them or
  leave all blank.
- **X regions** and **Y regions**: `Length [cm]` and `Cells` per region. The
  number of rows is `NR_X` / `NR_Y`; `Cells` counts cells and must be `>= 3`.
  X rows run left to right; Y rows bottom to top.
- **ZMAP**: one integer per region, rows are Y (bottom to top) and columns are
  X (left to right), values `1..NZ`. The grid resizes automatically when the
  region tables change.
- **QMAP**: one source value per region, `>= 0`.
- **Solver settings**: `N` (even, 2–18), `TOL` (Python range `1e-7 … 1e-2`)
  and the preferred solver (`NTS_DD` by default). The solver is stored as
  `_solver`, a hint that `nts-2d-config` also writes; the solver never changes
  the physics of the JSON.
- **input.txt preview**: the exact 11-parameter text the C solver receives.

### Buttons

| Button | Action |
|---|---|
| Load | Load the selected `config_2d_*.json` |
| New | Reset to the default configuration and pick the next free path |
| Validate | Pydantic validation; the status line shows the first errors |
| Save | Validate and write the JSON (with `_solver`) |

## Run tab

1. `Refresh` reloads `outputs/inputs/config_2d_*.json`.
2. Select one or more configurations (space toggles selection).
3. Choose the solver and the number of workers (1–4).
4. The preview shows the `input.txt` of the first selected configuration.
5. `Run selected` builds `input_NNN.txt`, executes the binary and writes
   `output_NNN.json` under `outputs/results/`.
6. `Cancel` terminates the running processes.

The log lists each start and finish with `STATUS`, `ITER`, `CPU` and the exact
output path, for example:

```text
[config_2d_001.json] started input_010.txt -> outputs/results/output_010.json
OK config_2d_001.json: STATUS=0 ITER=19 CPU=0.000584
   -> outputs/results/output_010.json
Output: outputs/results/output_010.json
```

`Output: ...` stays visible under the status line. `Plot latest` opens the
Plots tab with that file selected and `Results` opens the Results tab with it
selected. Results also appear automatically in the Results/Plots tabs when a
run finishes.

## Results tab

One row with `STATUS`, `ITER`, `CPU [s]`, `Grid` and `Mean flux`. Selecting a
row shows the file path, grid shape, mean, minimum and maximum flux. `Use in
Plots` switches to the Plots tab with that exact file selected.

Files written by the 1D solver (`output_1d_*.json`) are ignored because they
use a different schema.

## Plots tab

- The tab shows the results directory (`outputs/results/`) and the available
  files. A newly created result is selected automatically.
- Result selector plus a **Result path** field for files outside the results
  directory: type a path and press `Load path`.
- Optional input geometry. The matching `input_NNN.txt` is filled
  automatically; it provides the cm axes.
- Output PNG path (default: next free `outputs/results/plots/mflux_2d.png`).
- `Generate` runs matplotlib in a worker thread, so the UI does not freeze.
- The heatmap uses `origin="lower"`, `x [cm]` / `y [cm]` when the geometry is
  known, and a colorbar. Without geometry it falls back to cell indices.
- `Open` uses the desktop default application.
- With `textual-image` and a supported terminal, the PNG is shown inline.

## Files

```text
outputs/inputs/config_2d_###.json    editable configurations
outputs/inputs/input_###.txt         exact solver input
outputs/results/output_###.json      solver JSON (STATUS, ITER, CPU, MFLUX, ...)
outputs/results/plots/mflux_2d.png   heatmaps
outputs/logs/tui2d.log               diagnostics
```

## Differences from the 1D TUI

- The 1D UI is untouched; `nts tui` still opens it.
- The 2D TUI has no placeholders, Excel or `datos.json` tabs: those belong to
  the 1D pipeline.
- `MFLOW`, `XFLOW` and `YFLOW` are not displayed; the JSON keeps them.
- The domain map is 2D and proportional instead of the 1D geometry strip.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Solver binary not found` | `make -C solvers` (Linux) or `solvers/build_windows.ps1` |
| `STATUS=2` in a run | The input violates the contract; check BC values and `N` |
| Plot shows cell indices | Pass the matching `input_###.txt` in the geometry field |
| Map looks distorted | Region lengths are zero or negative; fix the X/Y tables |
| `Sigma_s must be lower than Sigma_t` | Fix the zone table |
| Inline preview missing | `uv sync --extra images` and a supported terminal |

## Tests

```bash
uv run python -m cli.run_tests -p "test_tui2d.py" -v
```
