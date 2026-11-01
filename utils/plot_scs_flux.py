#!/usr/bin/env python3
"""Plot SCS against scalar flux values from datos.json.

Usage:
    uv run nts-1d-plot [-i INPUT] [-o OUTPUT]

Reads the data produced by `nts-1d-data` (``datos.json`` by default) and
generates one subplot per requested position, plotting scalar flux against
SCS. The plot keys are discovered dynamically from the JSON entries
(``flux_<position>``), so any set of positions works.
"""

from pathlib import Path
import argparse
import json

import matplotlib


DEFAULT_INPUT = Path("outputs/results/datos.json")
DEFAULT_OUTPUT = Path("outputs/results/plots/scs_flux.png")


def load_data(path: Path) -> dict:
    with path.open("r") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="nts-1d-plot",
        description="Plot SCS vs scalar flux from datos.json",
    )
    parser.add_argument(
        "-i", "--input",
        default=DEFAULT_INPUT,
        type=Path,
        help=f"Path to the data JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        type=Path,
        help=f"Path for the PNG plot (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--x",
        choices=["SCS", "NU_SIGF", "k_eff"],
        default="SCS",
        help="Variable for the x-axis (default: SCS)",
    )
    args = parser.parse_args()

    data_path = args.input
    plot_path = args.output

    if not data_path.exists():
        raise FileNotFoundError(f"Input data not found: {data_path}")

    data = load_data(data_path)
    rows = data.get("data", [])
    if not rows:
        raise ValueError(f"No data found in {data_path}")

    rows = [row for row in rows if row.get(args.x) is not None]
    if not rows:
        raise ValueError(f"No rows with x={args.x!r} found in {data_path}")

    x_label = {
        "SCS": "SCS",
        "NU_SIGF": "nu*Sigma_f [cm^-1]",
        "k_eff": "k_eff",
    }[args.x]
    x_vals = [row[args.x] for row in rows]

    # Discover flux series dynamically (all flux_<position> keys present)
    flux_keys = sorted(
        (k for k in rows[0] if k.startswith("flux_")),
        key=lambda k: int(k.split("_", 1)[1]),
    )
    if not flux_keys:
        raise ValueError("No flux_* entries found in input data")

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from matplotlib.ticker import MultipleLocator

    fig, axes = plt.subplots(
        len(flux_keys), 1, figsize=(7.5, 4.2 * len(flux_keys)), dpi=150,
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
        ax.grid(True, which="major", linestyle="--", linewidth=0.6, alpha=0.5)
        ax.grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.4)
        ax.xaxis.set_major_locator(MultipleLocator(0.05))
        ax.xaxis.set_minor_locator(MultipleLocator(0.025))
        ax.legend()

    axes[-1].set_xlabel(x_label)

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(plot_path, bbox_inches="tight")
    plt.close(fig)

    print(f"✓ Plot saved: {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
