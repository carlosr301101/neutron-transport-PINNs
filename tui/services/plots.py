"""Plot generation for 1D results."""

from __future__ import annotations

from pathlib import Path

from utils.plot_1d_flux import (
    load_output,
    plot_angular,
    plot_datos,
    plot_k_history,
    plot_scalar,
    select_runs,
)

from .results import default_plot_path


def available_runs(result_path: Path | str) -> list[tuple[str, str]]:
    """Options for a run selector: ``(label, value)`` pairs."""
    runs = load_output(Path(result_path))
    options: list[tuple[str, str]] = [("All runs", "all")]
    for index, run in enumerate(runs):
        name = str(run.get("config_name", f"run_{index}"))
        mode = run.get("mode")
        label = f"{index}: {name}"
        if mode:
            label += f" ({mode})"
        options.append((label, name))
    return options


def generate(
    result_path: Path | str,
    kind: str,
    output: Path | str,
    *,
    run_selector: list[str] | None = None,
    datos_path: Path | str | None = None,
    x_key: str = "SCS",
) -> Path:
    """Generate one PNG and return its path."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if kind == "scs":
        if datos_path is None:
            raise ValueError("SCS plot requires a datos.json file.")
        plot_datos(Path(datos_path), output, x_key)
        return output

    runs = load_output(Path(result_path))
    selected = select_runs(runs, run_selector, kind)

    if kind == "scalar":
        plot_scalar(selected, output)
    elif kind == "angular":
        if len(selected) != 1:
            raise ValueError("Angular plot requires exactly one run.")
        plot_angular(selected[0], output)
    elif kind == "k-history":
        plot_k_history(selected, output)
    else:
        raise ValueError(f"Unknown plot kind: {kind}")

    return output


def suggested_output(kind: str) -> Path:
    return default_plot_path(kind)
