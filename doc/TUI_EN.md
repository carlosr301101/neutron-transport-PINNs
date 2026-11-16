# NTS 1D TUI

Terminal UI for the complete 1D workflow: configuration, runs, results,
plots, sweeps and exports.

> Scope: 1D only. The 2D C solvers remain CLI-only.
>
> Spanish version: [TUI.md](TUI.md).

## Launch

`uv run nts-tui` is the direct entry point and skips the CLI parser. `uv run
nts tui` uses a fast path that also avoids importing `cli.commands`.

Heavy modules (`pandas`, `matplotlib`, `openpyxl`) load only when needed.
Results and Plots read their result files when the tab is first activated.


```bash
uv run nts tui
# equivalent
uv run nts-tui
```

Optional inline image preview:

```bash
uv sync --extra images
```

The preview uses the terminal image protocol when available (Kitty, WezTerm,
iTerm2, sixel). Otherwise the PNG path is shown and the `Open` button uses the
desktop default application.

## Tabs

| Tab | Purpose |
|---|---|
| Dashboard | Version, config count, result count, latest result |
| Config | Full 1D wizard: geometry, materials, angular, fission, source, boundaries, convergence |
| Run | Select configs, optional scheme override, output JSON, Excel, live log, cancel |
| Results | Runs table with `k_eff`, `k_balance`, iterations and convergence |
| Plots | Scalar, angular, `k_history` and SCS plots with optional inline preview |
| Sweep | Placeholder ranges, preview, save JSON/Python, batch run |
| Export | `datos.json`, Excel workbook, SCS plot |

## Config tab

The form mirrors `Config.manual_input` and `nts-1d-config`:

- **Geometry and materials**: a geometry bar coloured by zone, an editable
  region table (`cells`, `length`, `zone`, `Q`) and an editable zone table
  (`Sigma_t`, `Sigma_s0`). Add or remove rows with the table buttons. `Q` is
  the external source per region (`0` = none); it is hidden and forced to zero
  in `eigenvalue`.
- **Physics mode**: `MODE` is the first field.
  - `fixed_source`: fission fields and the fission table are hidden; `NU_SIGF`
    is saved as zero.
  - `eigenvalue`: shows the fission table, `TOL_K`, `MAX_OUTER`, `K0` and the
    power fields; `K_EFF` is hidden.
  - `fixed_k`: shows the fission table, `K_EFF`, `TOL_K`, `MAX_OUTER` and the
    power fields.
  - `driven`: shows the fission table and power fields; `K_EFF` is hidden
    because the solver uses `k = 1`.
- **Fission per zone**: editable `nu*Sigma_f` and optional `Sigma_f` table.
- **Angular**: `N`, `SPATIAL_SCHEME`.
- **Source and boundaries**: `Q` is part of the region table; the rest are
  `reflex_izq`, `reflex_der`, `bound_left`, `bound_right`. A boundary scalar
  expands to `N/2` equal values; a full vector is kept. Example with `N=8`:
  `0` becomes `[0,0,0,0]`, `1` becomes `[1,1,1,1]`, and `[0,1,1,0]` is kept.
  Reflective sides hide the corresponding incoming-flux field.
- **Convergence**: `epsilon`, `max_iter`.

Only boundary arrays use comma-separated values. Numeric fields accept
placeholder names (`kk`, `mm`, ...) for later expansion in the Sweep tab.

Actions:

- `Validate`: runs the same `Config` validation as the CLI.
- `Save`: writes `outputs/inputs/config_1d_###.json` or the path in the form.
- `Load`: reads an existing config from the dropdown.
- `New`: resets the form to defaults.

## Run tab

- Select one or more configs.
- Optional scheme override (`DD`, `STEP`, `SC`).
- Output JSON path (blank uses the next `output_1d_###.json`).
- Excel switch writes the workbook next to the JSON.
- `Run selected` streams the CLI log. `Cancel` terminates the child process.

Configs with unresolved placeholders are rejected; expand them in Sweep first.

## Results tab

The table lists one row per run. Select a row to see mode, scheme, `k_eff`,
`k_balance`, outer iterations, flux updates, convergence and flux range.
`Use in Plots` sends the file to the Plot tab.

## Plots tab

- Result file and run selector.
- Kinds: scalar, angular, `k_history`.
- Angular plots always draw every direction (one line per component).
- Output PNG path (blank uses the next default name).
- `Open` opens the PNG with the desktop default application.
- SCS section: `datos.json`, x-axis (`SCS`, `NU_SIGF`, `k_eff`) and output PNG.

## Sweep tab

1. Load a config containing placeholders.
2. Fill `start`, `end` and `step` for each placeholder.
3. `Preview` shows the number of configs and the first one.
4. `Save` writes a JSON list or a `.py` file (`config_dict_###`).
5. `Run` executes the batch and writes one consolidated result file.

## Export tab

- `Extract flux`: writes `datos.json` for the given cell indices.
- `Write Excel`: exports the selected result file.
- `Write SCS plot`: plots `datos.json` against `SCS`, `NU_SIGF` or `k_eff`.

## Tests

```bash
uv run nts-test -p "test_tui_*.py" -v
```
