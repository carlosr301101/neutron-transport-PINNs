"""Excel export for consolidated 1D solver outputs (`nts-1d-excel`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
K_FORMAT = "0.0000000000"
FLUX_FORMAT = "0.000000E+00"
MU_FORMAT = "0.000000"
POWER_FORMAT = "0.000000E+00"


RUN_COLUMNS = [
    "run", "mode", "spatial_scheme", "k_eff", "k_balance", "k_converged",
    "iteration", "outer_iterations", "converged", "power_w", "power_scale", "power_unnormalized",
    "timestamp", "source", "error",
]
ZONE_COLUMNS = ["run", "zone", "Sigma_t", "Sigma_s", "nu_Sigma_f", "Sigma_f"]
REGION_COLUMNS = ["run", "region", "NC", "HR_cm", "IZL", "Q"]
BOUNDARY_COLUMNS = ["run", "side", "direction", "value"]
ANGULAR_COLUMNS = ["run", "cell", "x_cm", "direction", "mu", "psi"]
DIRECTION_COLUMNS = ["run", "direction", "mu", "omega"]
HISTORY_COLUMNS = ["run", "outer_iteration", "k_eff"]

def _run_name(run: dict, index: int) -> str:
    return str(run.get("config_name") or f"run_{index}")


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _centers(config: dict) -> list[float]:
    """Cell-centre x coordinates, same convention as the solver."""
    xs: list[float] = []
    x0 = 0.0
    for n_raw, h_raw in zip(_as_list(config.get("NC")), _as_list(config.get("HR"))):
        try:
            n, h = int(n_raw), float(h_raw)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        dx = h / n
        xs.extend(x0 + (i + 0.5) * dx for i in range(n))
        x0 += h
    return xs


def _metadata_sheet(payload: dict, runs: list[dict]) -> pd.DataFrame:
    fields = [
        ("solver", payload.get("solver")),
        ("generated_at", payload.get("generated_at")),
        ("total", len(runs)),
        ("failures", payload.get("failures")),
        ("spatial_schemes", ", ".join(payload.get("spatial_schemes") or [])),
    ]
    return pd.DataFrame(fields, columns=["Field", "Value"])


def _runs_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        rows.append(
            {
                "run": _run_name(run, i),
                "mode": run.get("mode"),
                "spatial_scheme": run.get("spatial_scheme"),
                "k_eff": run.get("k_eff"),
                "k_balance": run.get("k_balance"),
                "k_converged": run.get("k_converged"),
                "iteration": run.get("iteration"),
                "outer_iterations": run.get("outer_iterations"),
                "converged": run.get("converged"),
                "power_w": run.get("power_w"),
                "power_scale": run.get("power_scale"),
                "power_unnormalized": run.get("power_unnormalized"),
                "timestamp": run.get("timestamp"),
                "source": run.get("source"),
                "error": run.get("error"),
            }
        )
    return pd.DataFrame(rows, columns=RUN_COLUMNS)


def _zones_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        cfg = run.get("configuration") or {}
        sct = _as_list(cfg.get("SCT"))
        scs = _as_list(cfg.get("SCS"))
        nu_sigf = _as_list(cfg.get("NU_SIGF"))
        sigma_f = _as_list(cfg.get("SIGMA_F"))
        n_zones = max(len(sct), len(scs), len(nu_sigf), len(sigma_f))
        for z in range(n_zones):
            rows.append(
                {
                    "run": _run_name(run, i),
                    "zone": z + 1,
                    "Sigma_t": sct[z] if z < len(sct) else None,
                    "Sigma_s": scs[z] if z < len(scs) else None,
                    "nu_Sigma_f": nu_sigf[z] if z < len(nu_sigf) else None,
                    "Sigma_f": sigma_f[z] if z < len(sigma_f) else None,
                }
            )
    return pd.DataFrame(rows, columns=ZONE_COLUMNS)


def _regions_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        cfg = run.get("configuration") or {}
        nc = _as_list(cfg.get("NC"))
        hr = _as_list(cfg.get("HR"))
        izl = _as_list(cfg.get("IZL"))
        q = _as_list(cfg.get("Q"))
        n_regions = max(len(nc), len(hr), len(izl), len(q))
        for r in range(n_regions):
            rows.append(
                {
                    "run": _run_name(run, i),
                    "region": r + 1,
                    "NC": nc[r] if r < len(nc) else None,
                    "HR_cm": hr[r] if r < len(hr) else None,
                    "IZL": izl[r] if r < len(izl) else None,
                    "Q": q[r] if r < len(q) else None,
                }
            )
    return pd.DataFrame(rows, columns=REGION_COLUMNS)


def _boundaries_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        cfg = run.get("configuration") or {}
        for side, key in (("left", "bound_left"), ("right", "bound_right")):
            values = _as_list(cfg.get(key))
            for direction, value in enumerate(values, start=1):
                rows.append(
                    {
                        "run": _run_name(run, i),
                        "side": side,
                        "direction": direction,
                        "value": value,
                    }
                )
    return pd.DataFrame(rows, columns=BOUNDARY_COLUMNS)


def _scalar_flux_sheet(runs: list[dict]) -> pd.DataFrame:
    columns = {}
    length = 0
    for i, run in enumerate(runs):
        flux = _as_list(run.get("scalar_flux"))
        columns[_run_name(run, i)] = flux
        length = max(length, len(flux))
    data = {"cell": list(range(1, length + 1))}
    for name, flux in columns.items():
        data[name] = list(flux) + [None] * (length - len(flux))
    return pd.DataFrame(data)


def _angular_flux_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        angular = _as_list(run.get("angular_flux"))
        if not angular:
            continue
        cfg = run.get("configuration") or {}
        x = _centers(cfg)
        miu = _as_list(run.get("miu"))
        for cell, values in enumerate(angular, start=1):
            values = _as_list(values)
            for j, psi in enumerate(values):
                rows.append(
                    {
                        "run": _run_name(run, i),
                        "cell": cell,
                        "x_cm": x[cell - 1] if cell - 1 < len(x) else None,
                        "direction": j + 1,
                        "mu": miu[j] if j < len(miu) else None,
                        "psi": psi,
                    }
                )
    return pd.DataFrame(rows, columns=ANGULAR_COLUMNS)


def _directions_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        miu = _as_list(run.get("miu"))
        omega = _as_list(run.get("omega"))
        for j in range(max(len(miu), len(omega))):
            rows.append(
                {
                    "run": _run_name(run, i),
                    "direction": j + 1,
                    "mu": miu[j] if j < len(miu) else None,
                    "omega": omega[j] if j < len(omega) else None,
                }
            )
    return pd.DataFrame(rows, columns=DIRECTION_COLUMNS)


def _k_history_sheet(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for i, run in enumerate(runs):
        for iteration, k_eff in enumerate(_as_list(run.get("k_history")), start=1):
            rows.append(
                {"run": _run_name(run, i), "outer_iteration": iteration, "k_eff": k_eff}
            )
    return pd.DataFrame(rows, columns=HISTORY_COLUMNS)


SHEETS = (
    ("Metadata", _metadata_sheet, {}),
    ("Runs", _runs_sheet, {"k_eff": K_FORMAT, "k_balance": K_FORMAT,
                            "power_w": POWER_FORMAT, "power_scale": POWER_FORMAT,
                            "power_unnormalized": POWER_FORMAT}),
    ("Zones", _zones_sheet, {}),
    ("Regions", _regions_sheet, {}),
    ("Boundaries", _boundaries_sheet, {}),
    ("ScalarFlux", _scalar_flux_sheet, {}),
    ("AngularFlux", _angular_flux_sheet,
     {"mu": MU_FORMAT, "psi": FLUX_FORMAT, "x_cm": "0.0000"}),
    ("Directions", _directions_sheet, {"mu": MU_FORMAT, "omega": MU_FORMAT}),
    ("k_history", _k_history_sheet, {"k_eff": K_FORMAT}),
)


def _format_sheet(worksheet, formats: dict[str, str]) -> None:
    for cell in worksheet[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    headers = [cell.value for cell in worksheet[1]]
    for index, header in enumerate(headers, start=1):
        column = list(worksheet.columns)[index - 1]
        width = max(
            (len(str(cell.value)) for cell in column if cell.value is not None),
            default=8,
        )
        worksheet.column_dimensions[get_column_letter(index)].width = min(
            max(10, width + 2), 60
        )
        number_format = formats.get(header)
        if number_format:
            for cell in column[1:]:
                cell.number_format = number_format


def write_workbook(payload: dict, path: Path | str, runs: list[dict] | None = None) -> Path:
    """Write a consolidated 1D output payload to a formatted .xlsx workbook."""
    selected = list(payload.get("runs", [])) if runs is None else list(runs)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, builder, formats in SHEETS:
            frame = builder(payload, selected) if name == "Metadata" else builder(selected)
            frame.to_excel(writer, sheet_name=name, index=False)
            _format_sheet(writer.sheets[name], formats)
    return output


def _select_runs(runs: list[dict], selectors: list[str] | None) -> list[dict]:
    if not selectors:
        return runs
    chosen: list[dict] = []
    seen: set[int] = set()
    for selector in selectors:
        index = None
        if selector.isdigit():
            candidate = int(selector)
            if 0 <= candidate < len(runs):
                index = candidate
        else:
            for i, run in enumerate(runs):
                if run.get("config_name") == selector:
                    index = i
                    break
        if index is None:
            raise ValueError(f"run not found: {selector!r}")
        if index not in seen:
            chosen.append(runs[index])
            seen.add(index)
    return chosen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nts-1d-excel",
        description="Export a consolidated 1D JSON output to a formatted Excel workbook",
    )
    parser.add_argument("source", type=Path, help="Path to output_1d_###.json")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .xlsx (default: same stem as the JSON)",
    )
    parser.add_argument(
        "--run",
        nargs="+",
        metavar="NAME|INDEX",
        help="Only export these runs (name or 0-based index)",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.source.read_text())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        print("error: expected a consolidated output with runs[]", file=sys.stderr)
        return 1

    try:
        selected = _select_runs(payload["runs"], args.run)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output = args.output or args.source.with_suffix(".xlsx")
    try:
        write_workbook(payload, output, runs=selected)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"✓ Excel saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
