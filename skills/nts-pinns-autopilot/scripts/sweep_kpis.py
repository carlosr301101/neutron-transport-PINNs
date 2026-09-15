#!/usr/bin/env python3
"""Build comparative KPI tables from NTS 1D sweep outputs (output_1d_N*.json).

Usage:
    python sweep_kpis.py OUTPUT_1D_N4.json [OUTPUT_1D_N6.json ...] \
        [--positions 0 100] [--reference N]

Reads one or more NTS_DD_1D consolidated output JSONs, aligns runs by SCS,
and prints markdown tables:
  - iterations vs kk per order
  - flux at each requested position per order (index 0 = first cell centre)
  - max |flux(order) - flux(reference)| at the first position as the
    quadrature-convergence KPI

The last file given is treated as the reference order unless --reference
selects another one by its N suffix. Tables go to stdout so they can be
pasted directly into reports (e.g. a Resume.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def order_name(path: Path) -> str:
    """Guess an order label from the filename (output_1d_N6.json -> S6)."""
    m = re.search(r"(?:_|\b)N(\d+)", path.stem)
    return f"S{m.group(1)}" if m else path.stem


def load_sweep(path: Path, positions: list[int]) -> list[dict]:
    """Extract one row per config run, aligned by its SCS value."""
    data = json.load(path.open())
    rows = []
    for run in data.get("runs", []):
        sf = run["scalar_flux"]
        row = {
            "kk": run["configuration"]["SCS"][0],
            "iters": run["iteration"],
            "converged": run["converged"],
            **{f"flux_{p}": sf[p] for p in positions},
        }
        rows.append(row)
    rows.sort(key=lambda r: r["kk"])
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comparative KPI tables from NTS 1D sweep outputs"
    )
    parser.add_argument(
        "outputs", nargs="+", type=Path,
        help="output_1d_N*.json files; last one is the reference order",
    )
    parser.add_argument(
        "--positions", nargs="+", type=int, default=[0, 100],
        help="cell indices to report (default: 0 100)",
    )
    parser.add_argument(
        "--reference", type=int, default=None,
        help="N of the reference order (default: last file given)",
    )
    args = parser.parse_args(argv)

    positions = args.positions
    sweeps: dict[str, list[dict]] = {}
    sources: dict[str, Path] = {}
    for path in args.outputs:
        label = order_name(path)
        sources[label] = path
        sweeps[label] = load_sweep(path, positions)

    labels = list(sweeps)
    ref_label = f"S{args.reference}" if args.reference is not None else labels[-1]
    if ref_label not in sweeps:
        print(f"error: reference order {ref_label} not among inputs", file=sys.stderr)
        return 2

    ref_key = positions[0]

    # Validated runs
    print("## Validated runs\n")
    for label in labels:
        rows = sweeps[label]
        n_ok = sum(r["converged"] for r in rows)
        iters = [r["iters"] for r in rows]
        print(
            f"- **{label}** (`{sources[label]}`): {len(rows)} runs, "
            f"{n_ok} converged | iteraciones {min(iters)} → {max(iters)}"
        )
    print()

    # Iterations vs kk
    print("## Iterations vs kk\n")
    print("| kk | " + " | ".join(labels) + " |")
    print("|" + "------|" * (len(labels) + 1))
    for i, row in enumerate(sweeps[ref_label]):
        kk = f"{row['kk']:.2f}"
        cells = " | ".join(f"{sweeps[l][i]['iters']}" for l in labels)
        print(f"| {kk} | {cells} |")
    print()

    # Flux per position
    for pos in positions:
        key = f"flux_{pos}"
        print(f"## Scalar flux at position {pos}\n")
        print("| kk | " + " | ".join(labels) + " |")
        print("|------" * (len(labels) + 1) + "|")
        for i, row in enumerate(sweeps[ref_label]):
            kk = f"{row['kk']:.2f}"
            cells = " | ".join(
                (f"{sweeps[l][i][key]:.4f}" if 0.01 < abs(sweeps[l][i][key]) < 1000
                 else f"{sweeps[l][i][key]:.3e}")
                for l in labels
            )
            print(f"| {kk} | {cells} |")
        print()

    # Quadrature-convergence KPI vs reference
    print(f"## Quadrature convergence (Δ vs {ref_label}, position {positions[0]})\n")
    print("| " + " | ".join(f"max Δ({l} − {ref_label})" for l in labels[:-1]) + " |")
    print("|" + "------|" * (len(labels) - 1))
    for pos in [positions[0]]:
        deltas = []
        for l in labels[:-1]:
            d = max(
                abs(sweeps[l][i][f"flux_{pos}"] - sweeps[ref_label][i][f"flux_{pos}"])
                for i in range(len(sweeps[l]))
            )
            deltas.append(f"{d:.2e}")
        print("| " + " | ".join(deltas) + " |")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
