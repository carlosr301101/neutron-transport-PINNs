"""Read and summarize ``output_1d_*.json`` result files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.paths import PLOTS_DIR, RESULTS_DIR


def list_outputs() -> list[Path]:
    """All 1D result files, oldest first."""
    return sorted(RESULTS_DIR.glob("output_1d_*.json"))


def load_payload(path: Path | str) -> dict[str, Any]:
    """Load a consolidated output payload."""
    with Path(path).open("r") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object.")
    return payload


def summarize(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per run, with the fields shown in the results table."""
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
                "outer": run.get("iteration_eigenvalue") or run.get("outer_iterations"),
                "flux_updates": run.get("iteration", ""),
                "converged": run.get("converged"),
                "error": run.get("error", ""),
            }
        )
    return rows


def run_names(payload: dict[str, Any]) -> list[str]:
    """Names of the runs in a payload."""
    names: list[str] = []
    for index, run in enumerate(payload.get("runs", [])):
        if isinstance(run, dict):
            names.append(str(run.get("config_name", f"run_{index}")))
    return names


def next_result_path() -> Path:
    """Next free ``output_1d_###.json`` path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(RESULTS_DIR.glob("output_1d_*.json"))
    if not existing:
        index = 1
    else:
        try:
            index = int(existing[-1].stem.split("_")[-1]) + 1
        except ValueError:
            index = len(existing) + 1
    return RESULTS_DIR / f"output_1d_{index:03d}.json"


def unique_path(path: Path) -> Path:
    """Return *path* or a numbered sibling if it already exists."""
    if not path.exists():
        return path
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot find a free name for {path}")


def default_plot_path(kind: str) -> Path:
    names = {
        "scalar": "scalar_flux.png",
        "angular": "angular_flux.png",
        "k-history": "k_history.png",
        "scs": "scs_flux.png",
    }
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    return unique_path(PLOTS_DIR / names.get(kind, f"{kind}.png"))
