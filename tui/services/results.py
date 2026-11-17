"""Read and summarize ``output_1d_*.json`` result files."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from utils.paths import RESULTS_DIR

from .paths import numbered_path

# Parsed payloads are shared by Results, Plots and Export.  The key includes
# mtime and size so a rewritten output file is never served from the cache.
_CACHE: OrderedDict[Path, tuple[int, int, dict[str, Any]]] = OrderedDict()
_CACHE_MAX = 8


def list_outputs() -> list[Path]:
    """All 1D result files, oldest first."""
    return sorted(RESULTS_DIR.glob("output_1d_*.json"))


def load_payload(path: Path | str) -> dict[str, Any]:
    """Load a consolidated output payload, caching by path, mtime and size."""
    path = Path(path)
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    cached = _CACHE.get(path)
    if cached is not None and cached[:2] == key:
        _CACHE.move_to_end(path)
        return cached[2]

    with path.open("r") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{path} does not contain a JSON object.")

    _CACHE[path] = (key[0], key[1], payload)
    _CACHE.move_to_end(path)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return payload


def clear_cache() -> None:
    """Drop cached payloads (tests, or after out-of-band file edits)."""
    _CACHE.clear()


def summarize(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per run, with the fields shown in the results table.

    ``index`` keeps the position inside ``payload["runs"]`` so callers can map
    a table row back to the original run even when some entries are skipped.
    """
    rows: list[dict[str, Any]] = []
    for index, run in enumerate(payload.get("runs", [])):
        if not isinstance(run, dict):
            continue
        rows.append(
            {
                "index": index,
                "name": run.get("config_name", f"run_{index}"),
                "mode": run.get("mode", ""),
                "scheme": run.get("spatial_scheme", ""),
                "k_eff": run.get("k_eff"),
                "k_balance": run.get("k_balance"),
                "outer": _first_not_none(
                    run.get("iteration_eigenvalue"),
                    run.get("outer_iterations"),
                ),
                "flux_updates": run.get("iteration", ""),
                "converged": run.get("converged"),
                "error": run.get("error", ""),
            }
        )
    return rows


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def run_names(payload: dict[str, Any]) -> list[str]:
    """Names of the runs in a payload."""
    names: list[str] = []
    for index, run in enumerate(payload.get("runs", [])):
        if isinstance(run, dict):
            names.append(str(run.get("config_name", f"run_{index}")))
    return names


def next_result_path() -> Path:
    """Next free ``outputs/results/output_1d_###.json`` path."""
    return numbered_path(RESULTS_DIR, "output_1d_")
