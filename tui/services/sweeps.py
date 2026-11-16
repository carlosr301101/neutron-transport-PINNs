"""Placeholder expansion for parametric sweeps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.placeholders import (
    build_placeholder_values,
    contains_placeholders,
    decimal_places,
    replace_placeholders,
)


def expand_configs(
    base_config: dict[str, Any],
    ranges: dict[str, tuple[str | float, str | float, str | float]],
) -> list[dict[str, Any]]:
    """Expand one configuration over the placeholder ranges.

    ``ranges`` maps placeholder name to ``(start, end, step)``.  Values may be
    strings from the form; they are converted to floats here.
    """
    if not ranges:
        raise ValueError("Provide at least one placeholder range.")

    values: dict[str, list[float]] = {}
    rounding_digits = 0
    for name, (start, end, step) in ranges.items():
        start_f = float(start)
        end_f = float(end)
        step_f = float(step)
        values[name] = build_placeholder_values(start_f, end_f, step_f)
        rounding_digits = max(rounding_digits, decimal_places(str(step)))

    lengths = {name: len(items) for name, items in values.items()}
    if len(set(lengths.values())) != 1:
        raise ValueError(
            "Placeholder ranges have different lengths: "
            + ", ".join(f"{name}={length}" for name, length in lengths.items())
        )

    results: list[dict[str, Any]] = []
    for index in range(next(iter(lengths.values()))):
        replacements = {
            name: round(items[index], rounding_digits) for name, items in values.items()
        }
        expanded = replace_placeholders(base_config, replacements)
        if contains_placeholders(expanded, set(values)):
            raise ValueError("Unresolved placeholders after expansion.")
        results.append(expanded)
    return results


def save_configs(configs: list[dict[str, Any]], path: Path | str) -> Path:
    """Write expanded configs as JSON (`.json`) or Python (`.py`)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".py":
        chunks = []
        for index, config in enumerate(configs, start=1):
            chunks.append(
                f"config_dict_{index:03d} = "
                f"{json.dumps(config, indent=2, sort_keys=True)}\n"
            )
        path.write_text("\n".join(chunks))
    else:
        path.write_text(json.dumps(configs, indent=2) + "\n")
    return path
