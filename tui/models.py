"""Conversion between form text and the JSON configuration dictionary."""

from __future__ import annotations

from typing import Any

from core.placeholders import is_placeholder

from .schema import DEFAULT_CONFIG, FIELDS, Field


def _split_list(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    return [
        token for token in text.replace(";", ",").replace(" ", ",").split(",") if token
    ]


def parse_field(field: Field, raw: Any) -> Any:
    """Parse one form value.  Placeholders are kept as strings."""
    if field.kind == "bool":
        return bool(raw)
    if field.kind == "select":
        text = str(raw).strip() if raw is not None else ""
        return text or None
    if field.kind == "text":
        return "" if raw is None else str(raw)

    if field.kind in {"list_int", "list_float", "optional_list_float"}:
        if raw is None:
            tokens: list[str] = []
        elif isinstance(raw, (list, tuple)):
            tokens = [str(item).strip() for item in raw]
        else:
            tokens = _split_list(str(raw))

        if field.kind == "optional_list_float" and not tokens:
            return None

        converter = int if field.kind == "list_int" else float
        values: list[Any] = []
        for token in tokens:
            if not token:
                continue
            if is_placeholder(token):
                values.append(token)
                continue
            try:
                values.append(converter(token))
            except ValueError as exc:
                raise ValueError(f"{field.label}: invalid value {token!r}") from exc
        return values

    text = "" if raw is None else str(raw).strip()
    if not text:
        if field.kind == "optional_float":
            return None
        raise ValueError(f"{field.label} is required")

    if is_placeholder(text):
        return text

    try:
        if field.kind == "int":
            return int(text)
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field.label}: invalid value {text!r}") from exc


def format_field(field: Field, value: Any) -> Any:
    """Format one configuration value for a Textual widget."""
    if field.kind == "bool":
        return bool(value)
    if field.kind == "select":
        return "" if value is None else str(value)
    if field.kind in {"list_int", "list_float", "optional_list_float"}:
        if value is None:
            return ""
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def config_from_form(raw_values: dict[str, Any]) -> dict[str, Any]:
    """Build a configuration dictionary from form widget values."""
    config: dict[str, Any] = {}
    for field in FIELDS:
        config[field.key] = parse_field(field, raw_values.get(field.key, field.default))
    return config


def form_values_from_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Build form widget values from a configuration dictionary."""
    source = config or DEFAULT_CONFIG
    return {
        field.key: format_field(field, source.get(field.key, field.default))
        for field in FIELDS
    }
