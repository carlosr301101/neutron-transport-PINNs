#!/usr/bin/env python3
"""Plot 1D NTS results from output_1d_*.json or datos.json.

Modes:
  - scalar:    runs[].scalar_flux vs x
  - angular:   runs[].angular_flux vs x, one colored line per direction
  - k-history: runs[].k_history vs outer iteration
  - scs:       legacy datos.json mode (flux at positions vs SCS/NU_SIGF/k_eff)

Usage:
    uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind scalar
    uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind angular --run manual
    uv run nts-1d-plot -r outputs/results/output_1d_016.json --kind k-history --run manual
    uv run nts-1d-plot -i outputs/results/datos.json --x k_eff
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_DATOS = Path("outputs/results/datos.json")
DEFAULT_OUTPUTS = {
    "scalar": Path("outputs/results/plots/scalar_flux.png"),
    "angular": Path("outputs/results/plots/angular_flux.png"),
    "k-history": Path("outputs/results/plots/k_history.png"),
    "scs": Path("outputs/results/plots/scs_flux.png"),
}


# ---------------------------------------------------------------------------
# Data loading and run selection
# ---------------------------------------------------------------------------
def load_output(path: Path) -> list[dict]:
    """Load a raw output_1d_*.json and return its runs."""
    with path.open("r") as f:
        data = json.load(f)
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError(f"{path} does not contain a non-empty 'runs' list")
    return runs


def list_runs(runs: list[dict]) -> None:
    """Print the available runs with index, name, mode and k_eff."""
    print(f"{len(runs)} run(s):")
    for i, run in enumerate(runs):
        name = run.get("config_name", f"run_{i}")
        mode = run.get("mode", "?")
        k_eff = run.get("k_eff")
        suffix = f"  k_eff={k_eff:.8f}" if isinstance(k_eff, (int, float)) else ""
        print(f"  [{i}] {name}  mode={mode}{suffix}")


def select_runs(
    runs: list[dict], selector: list[str] | None, kind: str
) -> list[dict]:
    """Resolve --run names/indices. Requires a selector when there are >1 runs."""
    if not selector:
        if len(runs) == 1:
            return runs
        raise ValueError(
            "The file has multiple runs; use --run NAME|INDEX "
            "(or --run all for scalar/k-history) or --list-runs."
        )

    if selector == ["all"]:
        if kind == "angular":
            raise ValueError("--run all is not valid for --kind angular.")
        return runs

    selected = []
    for item in selector:
        if item.isdigit():
            index = int(item)
            if index < 0 or index >= len(runs):
                raise ValueError(f"Run index out of range: {index}")
            selected.append(runs[index])
        else:
            matches = [r for r in runs if r.get("config_name") == item]
            if not matches:
                raise ValueError(f"Run does not exist: {item!r}.")
            selected.append(matches[0])

    if kind == "angular" and len(selected) != 1:
        raise ValueError("--kind angular requires exactly one run.")
    return selected


def cell_centers(config: dict) -> np.ndarray:
    """Cell-centre x coordinates from configuration.NC / HR."""
    nc = config.get("NC")
    hr = config.get("HR")
    if not isinstance(nc, list) or not isinstance(hr, list):
        raise ValueError("configuration.NC/HR are not available.")
    nc = np.asarray(nc, dtype=int)
    hr = np.asarray(hr, dtype=float)
    if len(nc) != len(hr):
        raise ValueError("configuration.NC and HR have different lengths.")
    dx = np.concatenate([np.full(n, h / n) for n, h in zip(nc, hr)])
    return np.cumsum(dx) - 0.5 * dx


def _run_label(run: dict, index: int = 0) -> str:
    return str(run.get("config_name", f"run_{index}"))


def _k_text(run: dict) -> str:
    k_eff = run.get("k_eff")
    if isinstance(k_eff, (int, float)):
        return f"k_eff={k_eff:.8f}"
    return ""


def _save(fig, output: Path, show: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Plot modes
# ---------------------------------------------------------------------------
def plot_scalar(runs: list[dict], output: Path, show: bool = False) -> None:
    """Scalar flux vs x, one line per selected run."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    for i, run in enumerate(runs):
        phi = np.asarray(run["scalar_flux"], dtype=float)
        x = cell_centers(run.get("configuration", {}))
        if len(x) != len(phi):
            raise ValueError(
                f"{_run_label(run, i)}: scalar_flux ({len(phi)}) does not "
                f"match NC ({len(x)})"
            )
        label = _run_label(run, i)
        ktext = _k_text(run)
        if len(runs) > 1 and ktext:
            label = f"{label} ({ktext})"
        ax.plot(x, phi, "o-", ms=3, label=label)

    ax.set_xlabel("x [cm]")
    ax.set_ylabel("Scalar flux")
    if len(runs) == 1:
        run = runs[0]
        title = f"Scalar flux — {_run_label(run)}"
        if _k_text(run):
            title += f" ({_k_text(run)})"
        ax.set_title(title)
    else:
        ax.set_title("Scalar flux vs x")
        ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, output, show)


def plot_angular(
    run: dict,
    directions: list[int] | None,
    output: Path,
    show: bool = False,
) -> None:
    """Angular flux vs x: one colored line per direction on the same axes."""
    angular = np.asarray(run["angular_flux"], dtype=float)
    if angular.ndim == 1:
        angular = angular.reshape(-1, 1)
    x = cell_centers(run.get("configuration", {}))
    miu = run.get("miu")

    if miu is None:
        # Legacy files: (NTP, N/2) weighted sum w_m(psi+ + psi-), not raw psi.
        if angular.shape[0] == len(x) + 1:
            angular = angular[: len(x), :]
        if angular.shape[0] != len(x):
            raise ValueError(
                f"angular_flux ({angular.shape[0]}) does not match NC ({len(x)})"
            )
        labels = [f"direction {m}" for m in range(angular.shape[1])]
        ylabel = "Angular flux  ω_m(ψ⁺ + ψ⁻)"
        legend_title = "Direction"
    else:
        miu = np.asarray(miu, dtype=float)
        if angular.shape[0] != len(x) or angular.shape[1] != len(miu):
            raise ValueError(
                f"angular_flux {angular.shape} does not match "
                f"({len(x)} cells, {len(miu)} directions)"
            )
        labels = [f"μ={value:+.6f}" for value in miu]
        ylabel = "Angular flux ψ(x,μ)"
        legend_title = "Direction μ"

    n_directions = angular.shape[1]
    if directions is None:
        directions = list(range(n_directions))
    bad = [m for m in directions if m < 0 or m >= n_directions]
    if bad:
        raise ValueError(
            f"Directions out of range {bad}; there are {n_directions} directions "
            f"(0..{n_directions - 1})."
        )

    cmap = plt.get_cmap("viridis")
    if len(directions) == 1:
        colors = [cmap(0.0)]
    else:
        colors = [cmap(i / (len(directions) - 1)) for i in range(len(directions))]

    fig, ax = plt.subplots(figsize=(8.0, 4.5), dpi=150)
    for color, m in zip(colors, directions):
        ax.plot(
            x,
            angular[:, m],
            "o-",
            ms=3,
            color=color,
            label=labels[m],
        )

    ax.set_xlabel("x [cm]")
    ax.set_ylabel(ylabel)
    title = f"Angular flux — {_run_label(run)}"
    if _k_text(run):
        title += f" ({_k_text(run)})"
    ax.set_title(title)
    ax.legend(title=legend_title, ncol=1)
    ax.grid(alpha=0.3)
    _save(fig, output, show)


def plot_k_history(
    runs: list[dict], output: Path, show: bool = False
) -> None:
    """k_eff vs outer iteration, one line per run with history."""
    usable = []
    for run in runs:
        history = run.get("k_history") or []
        if history:
            usable.append((run, np.asarray(history, dtype=float)))
    if not usable:
        raise ValueError(
            "No k_history in the selected runs. "
            "Only MODE=eigenvalue stores history."
        )

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    for run, history in usable:
        x = np.arange(1, len(history) + 1)
        label = _run_label(run)
        ax.plot(x, history, "o-", ms=3, label=label)
        k_eff = run.get("k_eff")
        if isinstance(k_eff, (int, float)):
            ax.axhline(
                k_eff,
                ls="--",
                lw=1,
                color=ax.lines[-1].get_color(),
                label=f"{label} final = {k_eff:.8f}",
            )

    ax.set_xlabel("Outer iteration")
    ax.set_ylabel("k_eff")
    ax.set_title("k_eff history")
    ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, output, show)


def plot_datos(
    path: Path, output: Path, x_key: str, show: bool = False
) -> None:
    """Legacy datos.json mode: flux at positions vs SCS/NU_SIGF/k_eff."""
    with path.open("r") as f:
        data = json.load(f)
    rows = data.get("data", [])
    if not rows:
        raise ValueError(f"No data found in {path}")

    rows = [row for row in rows if row.get(x_key) is not None]
    if not rows:
        raise ValueError(f"No rows with {x_key!r} found in {path}")

    x_label = {
        "SCS": "SCS",
        "NU_SIGF": "nu*Sigma_f [cm^-1]",
        "k_eff": "k_eff",
    }[x_key]
    x_vals = [row[x_key] for row in rows]

    flux_keys = sorted(
        (k for k in rows[0] if k.startswith("flux_")),
        key=lambda k: int(k.split("_", 1)[1]),
    )
    if not flux_keys:
        raise ValueError("No flux_* entries found in input data")

    fig, axes = plt.subplots(
        len(flux_keys),
        1,
        figsize=(7.5, 4.2 * len(flux_keys)),
        dpi=150,
        sharex=True,
    )
    if len(flux_keys) == 1:
        axes = [axes]

    for ax, key in zip(axes, flux_keys):
        position = key.split("_", 1)[1]
        values = [row[key] for row in rows]
        ax.plot(x_vals, values, marker="o", label=f"Flux at position {position}")
        ax.set_title(f"Scalar Flux vs {x_label} (Position {position})")
        ax.set_ylabel("Scalar Flux")
        ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
        ax.legend()

    axes[-1].set_xlabel(x_label)
    _save(fig, output, show)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nts-1d-plot",
        description=(
            "Plot 1D scalar flux, angular flux, k_history or datos.json"
        ),
    )
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        "-r",
        "--result",
        type=Path,
        help="Raw output_1d_*.json with runs[]",
    )
    input_group.add_argument(
        "-i",
        "--input",
        type=Path,
        help=f"datos.json for --kind scs (default: {DEFAULT_DATOS})",
    )
    parser.add_argument(
        "--kind",
        choices=["scalar", "angular", "k-history", "scs"],
        default=None,
        help="Plot type (default: scalar with -r, scs with -i)",
    )
    parser.add_argument(
        "--run",
        nargs="+",
        metavar="RUN",
        help="Run name/index to plot; 'all' for scalar/k-history",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List the runs in -r and exit",
    )
    parser.add_argument(
        "--directions",
        nargs="+",
        type=int,
        metavar="M",
        help="Angular directions to plot (default: all)",
    )
    parser.add_argument(
        "--x",
        choices=["SCS", "NU_SIGF", "k_eff"],
        default="SCS",
        help="x-axis for --kind scs (default: SCS)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output PNG (default: outputs/results/plots/<kind>.png)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Call plt.show() after saving (may be a no-op in headless)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.result is None and args.input is None:
        args.input = DEFAULT_DATOS

    if args.list_runs and args.result is None:
        parser.error("--list-runs requires -r/--result")

    kind = args.kind
    if kind is None:
        kind = "scalar" if args.result is not None else "scs"

    if kind == "scs":
        if args.result is not None:
            parser.error("--kind scs requires -i/--input (datos.json)")
        if args.run or args.list_runs or args.directions:
            parser.error(
                "--run/--list-runs/--directions are only for -r/--result"
            )
        output = args.output or DEFAULT_OUTPUTS["scs"]
        try:
            plot_datos(args.input, output, args.x, args.show)
        except (ValueError, KeyError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"✓ Plot saved: {output}")
        return 0

    if args.result is None:
        parser.error(f"--kind {kind} requires -r/--result")
    if args.x != "SCS":
        parser.error("--x is only valid with --kind scs")
    if args.directions and kind != "angular":
        parser.error("--directions is only valid with --kind angular")

    runs = load_output(args.result)

    if args.list_runs:
        list_runs(runs)
        return 0

    try:
        selected = select_runs(runs, args.run, kind)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Available runs:", file=sys.stderr)
        list_runs(runs)
        return 2

    output = args.output or DEFAULT_OUTPUTS[kind]

    try:
        if kind == "scalar":
            plot_scalar(selected, output, args.show)
        elif kind == "angular":
            if args.directions and len(selected) != 1:
                raise ValueError("--directions requires exactly one run.")
            plot_angular(selected[0], args.directions, output, args.show)
        elif kind == "k-history":
            plot_k_history(selected, output, args.show)
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"✓ Plot saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
