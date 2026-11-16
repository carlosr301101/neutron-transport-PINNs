"""Read, write and validate 1D configuration JSON files."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Any

from core.placeholders import detect_placeholders
from solvers.runners.NTS_DD_1D import Config

from utils.paths import INPUTS_DIR


def list_configs() -> list[Path]:
    """All ``config_1d_*.json`` files, oldest first."""
    return sorted(INPUTS_DIR.glob("config_1d_*.json"))


def next_config_path() -> Path:
    """Next free ``outputs/inputs/config_1d_###.json`` path."""
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(INPUTS_DIR.glob("config_1d_*.json"))
    if not existing:
        index = 1
    else:
        try:
            index = int(existing[-1].stem.split("_")[-1]) + 1
        except ValueError:
            index = len(existing) + 1
    return INPUTS_DIR / f"config_1d_{index:03d}.json"


def load_config(path: Path | str) -> dict[str, Any]:
    """Load one configuration object from JSON."""
    path = Path(path)
    with path.open("r") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        if len(data) != 1 or not isinstance(data[0], dict):
            raise ValueError(
                f"{path} contains a list; expected one configuration object."
            )
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object.")
    return data


def save_config(path: Path | str, config: dict[str, Any]) -> Path:
    """Write one configuration object, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def validate_config(config: dict[str, Any]) -> tuple[list[str], str]:
    """Validate a configuration dictionary.

    Returns ``(errors, message)``.  Placeholders are reported but not sent to
    ``Config`` because it only understands concrete numbers.
    """
    placeholders = detect_placeholders(config)
    if placeholders:
        names = ", ".join(sorted(placeholders))
        return [], f"Placeholders detected ({names}); expand them with Sweep."

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            Config(manual=False, **config)
    except Exception as exc:  # noqa: BLE001 - surface the exact message
        return [str(exc)], "Invalid configuration."

    return [], "Configuration is valid."
