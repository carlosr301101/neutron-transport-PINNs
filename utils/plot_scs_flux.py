#!/usr/bin/env python3
"""Plot SCS against scalar flux values from datos.json."""

from pathlib import Path
import json

import matplotlib


def load_data(path: Path) -> dict:
    with path.open("r") as f:
        return json.load(f)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    data_path = root / "outputs" / "results" / "datos.json"
    plot_path = root / "outputs" / "results" / "plots" / "scs_flux.png"

    if not data_path.exists():
        raise FileNotFoundError(f"datos.json not found: {data_path}")

    data = load_data(data_path)
    rows = data.get("data", [])
    if not rows:
        raise ValueError("No data found in datos.json")

    scs_vals = [row["SCS"] for row in rows]
    flux_0 = [row["flux_0"] for row in rows]
    flux_100 = [row["flux_100"] for row in rows]

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from matplotlib.ticker import MultipleLocator

    fig, axes = plt.subplots(2, 1, figsize=(7.5, 8.5), dpi=150, sharex=True)

    axes[0].plot(scs_vals, flux_0, marker="o", label="Flux at position 0")
    axes[0].set_title("Scalar Flux vs SCS (Position 0)")
    axes[0].set_ylabel("Scalar Flux")
    axes[0].xaxis.set_major_locator(MultipleLocator(0.05))
    axes[0].xaxis.set_minor_locator(MultipleLocator(0.025))
    axes[0].grid(True, which="major", linestyle="--", linewidth=0.6, alpha=0.5)
    axes[0].grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.4)
    axes[0].legend()

    axes[1].plot(scs_vals, flux_100, marker="s", label="Flux at position 100")
    axes[1].set_title("Scalar Flux vs SCS (Position 100)")
    axes[1].set_xlabel("SCS")
    axes[1].set_ylabel("Scalar Flux")
    axes[1].xaxis.set_major_locator(MultipleLocator(0.05))
    axes[1].xaxis.set_minor_locator(MultipleLocator(0.025))
    axes[1].grid(True, which="major", linestyle="--", linewidth=0.6, alpha=0.5)
    axes[1].grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.4)
    axes[1].legend()

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(plot_path, bbox_inches="tight")
    plt.close(fig)

    print(f"✓ Plot saved: {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
