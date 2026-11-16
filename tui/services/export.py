"""Excel, datos.json and SCS plot helpers."""

from __future__ import annotations

import json
from pathlib import Path

from utils.extract_1d_flux import extract_flux
from utils.paths import INPUTS_DIR, RESULTS_DIR

from .results import load_payload, unique_path


def parse_positions(text: str) -> list[int]:
    """Parse comma/space separated cell indices."""
    tokens = text.replace(",", " ").split()
    positions: list[int] = []
    for token in tokens:
        try:
            value = int(token)
        except ValueError as exc:
            raise ValueError(f"Invalid position: {token!r}") from exc
        if value < 0:
            raise ValueError(f"Position must be >= 0, got {value}")
        positions.append(value)
    if not positions:
        raise ValueError("Provide at least one cell index.")
    return positions


def extract_positions(
    source: Path | str,
    positions: list[int],
    output: Path | str,
    inputs_path: Path | str | None = None,
) -> Path:
    """Run the ``nts-1d-data`` extraction and write datos.json."""
    source = Path(source)
    output = Path(output)
    inputs = Path(inputs_path) if inputs_path else INPUTS_DIR / "inputs.py"
    payload = extract_flux(source, inputs, positions)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    return output


def default_datos_path() -> Path:
    return RESULTS_DIR / "datos.json"


def write_excel(result_path: Path | str, output_path: Path | str | None = None) -> Path:
    """Write the Excel workbook for one consolidated result file."""
    from utils.excel_1d import write_workbook  # noqa: PLC0415 - lazy by design

    result_path = Path(result_path)
    payload = load_payload(result_path)
    if output_path is None:
        target = unique_path(result_path.with_suffix(".xlsx"))
    else:
        target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_workbook(payload, target)
    return target


def write_scs_plot(
    datos_path: Path | str,
    output: Path | str,
    x_key: str,
) -> Path:
    """Write the legacy SCS/NU_SIGF/k_eff plot from datos.json."""
    from utils.plot_1d_flux import plot_datos  # noqa: PLC0415 - lazy by design

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    plot_datos(Path(datos_path), output, x_key)
    return output
