"""Read, write and validate 2D configuration JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tui.services.paths import numbered_path
from utils.paths import INPUTS_DIR

from ..models import DEFAULT_CONFIG, validate_config

CONFIG_GLOB = "config_2d_*.json"


def list_configs() -> list[Path]:
    """All ``config_2d_*.json`` files, oldest first."""
    return sorted(INPUTS_DIR.glob(CONFIG_GLOB))


def next_config_path() -> Path:
    """Next free ``outputs/inputs/config_2d_###.json`` path."""
    return numbered_path(INPUTS_DIR, "config_2d_")


def load_config(path: Path | str) -> dict[str, Any]:
    """Load one 2D configuration object from JSON."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object.")
    return data


def save_config(
    path: Path | str, config: dict[str, Any], solver: str | None = None
) -> Path:
    """Write one configuration object, creating parent directories."""
    path = Path(path)
    data = dict(config)
    if solver:
        data["_solver"] = solver
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def validate(config: dict[str, Any]) -> tuple[list[str], str]:
    """Delegate to the shared Pydantic validation."""
    return validate_config(config)


def default_config() -> dict[str, Any]:
    """Deep-ish copy of the default so widgets never share nested lists."""
    return json.loads(json.dumps(DEFAULT_CONFIG))
