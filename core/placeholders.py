"""Shared placeholder expansion helpers.

The 1D configuration wizard accepts symbolic names (``kk``, ``mm``, ...)
instead of numbers.  ``nts-generate`` expands those names into a grid of
concrete configurations.  The CLI and the TUI both use the helpers here so
the expansion rules cannot drift apart.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

PLACEHOLDER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")

# Enum-like fields and metadata whose string values are not placeholders.
_TEXT_KEYS = {"SPATIAL_SCHEME", "MODE", "ZONE_NAMES"}


def is_placeholder(value: object) -> bool:
    """True when *value* looks like a symbolic placeholder name."""
    return isinstance(value, str) and PLACEHOLDER_RE.fullmatch(value) is not None


def detect_placeholders(value: object, skip_keys: set[str] | None = None) -> set[str]:
    """Collect placeholder names from a configuration mapping.

    Strings in enum fields (``SPATIAL_SCHEME``, ``MODE``) are ignored.  The
    function descends into lists and dictionaries.
    """
    skip = set(_TEXT_KEYS)
    if skip_keys:
        skip.update(skip_keys)

    found: set[str] = set()

    def visit(item: object, key: str | None = None) -> None:
        if key in skip:
            return
        if isinstance(item, dict):
            for child_key, child in item.items():
                visit(child, child_key)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child, key)
        elif is_placeholder(item):
            found.add(str(item))

    visit(value)
    return found


def build_placeholder_values(start: float, end: float, step: float) -> list[float]:
    """Build an inclusive arithmetic grid, clipping the last point to *end*."""
    if step <= 0:
        raise ValueError("Step must be greater than 0")
    if end < start:
        raise ValueError("End must be greater than or equal to start")

    values: list[float] = []
    index = 0
    epsilon = 1e-12
    while True:
        value = start + (step * index)
        if value > end + epsilon:
            break
        if value > end:
            value = end
        values.append(value)
        index += 1

    if not values:
        values.append(start)

    return values


def replace_placeholders(value, replacements: dict[str, float]):
    """Return *value* with every placeholder name replaced recursively."""
    if isinstance(value, dict):
        return {
            key: (
                child
                if key in _TEXT_KEYS
                else replace_placeholders(child, replacements)
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [replace_placeholders(child, replacements) for child in value]
    if isinstance(value, tuple):
        return tuple(replace_placeholders(child, replacements) for child in value)
    if isinstance(value, str) and value in replacements:
        return replacements[value]
    return value


def contains_placeholders(value, placeholder_names: set[str]) -> bool:
    """True when any of *placeholder_names* remains in *value*."""
    if isinstance(value, dict):
        return any(
            contains_placeholders(child, placeholder_names)
            for key, child in value.items()
            if key not in _TEXT_KEYS
        )
    if isinstance(value, (list, tuple)):
        return any(contains_placeholders(child, placeholder_names) for child in value)
    if isinstance(value, str):
        return value in placeholder_names
    return False


def decimal_places(value_str: str) -> int:
    """Number of decimal places in a numeric string (0 for integers)."""
    try:
        decimal_value = Decimal(value_str)
    except InvalidOperation, ValueError:
        return 0

    exponent = decimal_value.as_tuple().exponent
    return -exponent if exponent < 0 else 0
