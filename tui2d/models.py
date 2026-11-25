"""Configuration helpers shared by the 2D TUI panes.

The TUI keeps plain dictionaries in the widgets and converts them to
``SimulationConfig`` only for validation, preview and saving.  The contract is
the one in ``doc/2D_SOLVERS_CONTRACT.md``: ``BC`` is
``[left, bottom, right, top]`` with ``-1.0`` reflective, ``0.0`` vacuum and
positive incoming flux.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from core.config import SimulationConfig
from core.input_builder import InputBuilder
from utils.paths import AVAILABLE_SOLVERS

SOLVER_NAMES = tuple(AVAILABLE_SOLVERS)
DEFAULT_SOLVER = "NTS_DD"

DEFAULT_CONFIG: dict[str, Any] = {
    "N": 4,
    "NZ": 1,
    "zones": [{"sigma_t": 0.5, "sigma_s": 0.3}],
    "NR_X": 1,
    "XDOM": [{"length": 10.0, "nodes": 5}],
    "NR_Y": 1,
    "YDOM": [{"length": 10.0, "nodes": 5}],
    "ZMAP": [[1]],
    "QMAP": [[1.0]],
    "BC": [0.0, 0.0, 0.0, 0.0],
    "TOL": 1e-5,
}

EVEN_ORDERS = tuple(range(2, 19, 2))


def clean_config(config: dict[str, Any]) -> dict[str, Any]:
    """Drop comment/hint keys (``_solver``, ``_comment``, ...)."""
    return {key: value for key, value in config.items() if not str(key).startswith("_")}


def config_model(config: dict[str, Any]) -> SimulationConfig:
    """Validate a dictionary and return the Pydantic model."""
    return SimulationConfig.model_validate(clean_config(config))


def validate_config(config: dict[str, Any]) -> tuple[list[str], str]:
    """Return ``(errors, message)`` for a configuration dictionary."""
    try:
        model = config_model(config)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(part) for part in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        return errors, "Invalid configuration."
    except Exception as exc:  # noqa: BLE001 - surface the exact message
        return [str(exc)], "Invalid configuration."

    return [], (
        f"Configuration is valid ({model.N} ordinates, "
        f"{model.total_nodes_x}x{model.total_nodes_y} cells)."
    )


def build_preview(config: dict[str, Any], max_lines: int | None = None) -> str:
    """Return the ``input.txt`` that the configured solver would receive."""
    builder = InputBuilder(config_model(config))
    return builder.build() if max_lines is None else builder.preview(max_lines)


def count_lines(text: str) -> int:
    """Number of non-empty lines in an input preview."""
    return len([line for line in text.splitlines() if line.strip()])
