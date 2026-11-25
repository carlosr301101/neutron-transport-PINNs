"""Summarize 2D ``output_*.json`` result files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tui.services.paths import numbered_path
from utils.paths import RESULTS_DIR


def list_outputs() -> list[Path]:
    """All 2D result files, oldest first.

    The 1D solver writes ``output_1d_*.json`` with a different schema, so those
    files are excluded.
    """
    return sorted(
        path
        for path in RESULTS_DIR.glob("output_*.json")
        if not path.name.startswith("output_1d_")
    )


def load_result(path: Path | str) -> dict[str, Any]:
    """Load one result JSON object."""
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object.")
    return data


def summarize(path: Path | str) -> dict[str, Any]:
    """Return the fields shown in the results table."""
    data = load_result(path)
    mflux = data.get("MFLUX")
    rows = cols = 0
    mean = None
    values: list[float] = []
    if isinstance(mflux, list) and mflux and isinstance(mflux[0], list):
        rows = len(mflux)
        cols = len(mflux[0])
        values = [
            value for row in mflux for value in row if isinstance(value, (int, float))
        ]
        if values:
            mean = sum(values) / len(values)

    return {
        "path": Path(path),
        "status": data.get("STATUS"),
        "iterations": data.get("ITER"),
        "cpu": data.get("CPU"),
        "rows": rows,
        "cols": cols,
        "mean": mean,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def find_input_for_result(result_path: Path | str) -> Path | None:
    """Return the ``input`` file that produced a result, if it can be found.

    The default runner writes ``input_NNN.txt`` next to ``output_NNN.json``
    (well, in the inputs directory). A custom output name pairs with
    ``<stem>.txt`` in the inputs directory or next to the result file.
    """
    from utils.paths import INPUTS_DIR

    path = Path(result_path)
    stem = path.stem
    candidates: list[Path] = []

    parts = stem.split("_")
    if len(parts) >= 2 and parts[0] == "output":
        candidates.append(INPUTS_DIR / f"input_{parts[1]}.txt")
    candidates.append(INPUTS_DIR / f"{stem}.txt")
    candidates.append(path.parent / f"{stem}.txt")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def next_output_path() -> Path:
    """Next free ``outputs/results/output_NNN.json`` path."""
    return numbered_path(RESULTS_DIR, "output_")
