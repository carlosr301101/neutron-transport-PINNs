"""Heatmap generation for 2D results."""

from __future__ import annotations

from pathlib import Path

from core.input_reader import read_input
from tui.services.paths import unique_path
from utils.paths import PLOTS_DIR

from .results import find_input_for_result, load_result


def default_plot_path() -> Path:
    """Collision-free default PNG path."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    return unique_path(PLOTS_DIR / "mflux_2d.png")


def generate_heatmap(
    result_path: Path | str,
    output: Path | str,
    input_path: Path | str | None = None,
) -> Path:
    """Write a ``MFLUX`` heatmap PNG, using cm axes when geometry is known."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    data = load_result(result_path)
    mflux = data.get("MFLUX")
    if not isinstance(mflux, list) or not mflux or not isinstance(mflux[0], list):
        raise ValueError(
            f"{result_path}: STATUS={data.get('STATUS')} has no MFLUX matrix."
        )

    geometry_path = (
        Path(input_path) if input_path else find_input_for_result(result_path)
    )
    extent = None
    if geometry_path is not None and geometry_path.is_file():
        geometry = read_input(geometry_path)
        if (len(mflux), len(mflux[0])) == (
            geometry.total_nodes_y,
            geometry.total_nodes_x,
        ):
            extent = geometry.extent

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 6.0), dpi=150)
    if extent is not None:
        image = ax.imshow(
            mflux,
            origin="lower",
            cmap="viridis",
            aspect="auto",
            extent=extent,
        )
        ax.set_xlabel("x [cm]")
        ax.set_ylabel("y [cm]")
    else:
        image = ax.imshow(mflux, origin="lower", cmap="viridis", aspect="auto")
        ax.set_xlabel("X cell index")
        ax.set_ylabel("Y cell index")

    status = data.get("STATUS")
    iterations = data.get("ITER")
    title = "Neutron Flux (MFLUX)"
    if status is not None:
        title += f" · STATUS={status}"
    if iterations is not None:
        title += f" · ITER={iterations}"
    ax.set_title(title)

    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Flux intensity")

    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output
