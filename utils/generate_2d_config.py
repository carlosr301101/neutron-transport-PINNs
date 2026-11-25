#!/usr/bin/env python3
"""Interactive generator for NTS 2D configuration JSON files.

The wizard asks for the same values that ``nts validate`` / ``nts generate``
consume and rejects invalid input before writing anything.  Boundary
conditions follow the canonical C-solver order ``[left, bottom, right, top]``:

    -1.0  reflective
     0.0  vacuum
     > 0  incoming flux

Usage::

    uv run nts-2d-config -o caso.json
    uv run nts validate caso.json
    uv run nts generate caso.json -p
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import (  # noqa: E402
    BC_LABELS,
    SimulationConfig,
    describe_bc,
    is_valid_bc,
)
from utils.console import emit  # noqa: E402
from utils.paths import AVAILABLE_SOLVERS, INPUTS_DIR  # noqa: E402


class Cancelled(Exception):
    """Raised when the user aborts the wizard."""


def next_config_path(base: Path | None = None) -> Path:
    """Return the next free ``outputs/inputs/config_2d_###.json`` path."""
    base = INPUTS_DIR if base is None else base
    base.mkdir(parents=True, exist_ok=True)
    existing = sorted(base.glob("config_2d_*.json"))
    if not existing:
        index = 1
    else:
        try:
            index = int(existing[-1].stem.split("_")[-1]) + 1
        except ValueError:
            index = len(existing) + 1
    return base / f"config_2d_{index:03d}.json"


def _read(prompt: str) -> str:
    """Read one line, converting EOF/interrupt into :class:`Cancelled`."""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError) as exc:
        raise Cancelled from exc


def _ask_value(prompt, default, parse, validate=None):
    """Prompt until *parse* and *validate* accept the value."""
    while True:
        raw = _read(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = parse(raw)
            if validate is not None:
                validate(value)
        except ValueError as exc:
            emit(f"  Error: {exc}")
            continue
        return value


def _in_range(minimum=None, maximum=None, exclusive_min=False):
    def check(value):
        if minimum is not None:
            bad = value <= minimum if exclusive_min else value < minimum
            if bad:
                comparator = ">" if exclusive_min else ">="
                raise ValueError(f"value must be {comparator} {minimum}, got {value}")
        if maximum is not None and value > maximum:
            raise ValueError(f"value must be <= {maximum}, got {value}")

    return check


def _ask_int(prompt, default, minimum=None, maximum=None, exclusive_min=False):
    return _ask_value(
        prompt,
        default,
        int,
        _in_range(minimum, maximum, exclusive_min=exclusive_min),
    )


def _ask_float(prompt, default, minimum=None, maximum=None, exclusive_min=False):
    return _ask_value(
        prompt,
        default,
        float,
        _in_range(minimum, maximum, exclusive_min=exclusive_min),
    )


def _ask_even(prompt, default, minimum=2, maximum=18):
    def check(value):
        _in_range(minimum, maximum)(value)
        if value % 2 != 0:
            raise ValueError(f"value must be even, got {value}")

    return _ask_value(prompt, default, int, check)


def _ask_bc(prompt, default=0.0):
    def check(value):
        if not is_valid_bc(value):
            raise ValueError(
                "-1.0 (reflective), 0.0 (vacuum) or > 0 (incoming flux) expected"
            )

    return _ask_value(prompt, default, float, check)


def _ask_row(prompt, count, parse, validate=None):
    """Prompt for a row of *count* values separated by spaces or commas."""
    while True:
        raw = _read(prompt).strip()
        parts = raw.replace(",", " ").split()
        if len(parts) != count:
            emit(f"  Error: expected {count} values, got {len(parts)}")
            continue
        try:
            values = [parse(item) for item in parts]
            if validate is not None:
                for value in values:
                    validate(value)
        except ValueError as exc:
            emit(f"  Error: {exc}")
            continue
        return values


def _ask_solver(default="NTS_DD") -> str:
    options = ", ".join(AVAILABLE_SOLVERS)
    while True:
        raw = _read(f"Solver [{default}] ({options}): ").strip()
        if not raw:
            return default
        name = raw.upper()
        if name in AVAILABLE_SOLVERS:
            return name
        emit(f"  Error: unknown solver {raw!r}; choose one of {options}")


def build_config_interactively() -> tuple[SimulationConfig, str]:
    """Run the wizard and return the validated config plus preferred solver."""
    emit("\n=== NTS 2D configuration wizard ===")
    emit("Boundary conditions use the order: left, bottom, right, top.")
    emit("-1.0 = reflective | 0.0 = vacuum | > 0 = incoming flux\n")

    N = _ask_even("Quadrature order (N)", 4)
    NZ = _ask_int("Number of material zones (NZ)", 1, minimum=1)

    zones = []
    for zone_index in range(1, NZ + 1):
        emit(f"\nZone {zone_index}/{NZ}")
        sigma_t = _ask_float(
            "  sigma_t [1/cm]", 0.5, minimum=0.0, exclusive_min=True
        )

        def check_scattering(value, sigma_t=sigma_t):
            if value < 0:
                raise ValueError(f"sigma_s must be >= 0, got {value}")
            if value >= sigma_t:
                raise ValueError(
                    f"sigma_s ({value}) must be lower than sigma_t ({sigma_t})"
                )

        sigma_s = _ask_value("  sigma_s [1/cm]", 0.3, float, check_scattering)
        zones.append({"sigma_t": sigma_t, "sigma_s": sigma_s})

    emit("\nX direction")
    NR_X = _ask_int("  Number of X regions (NR_X)", 1, minimum=1)
    XDOM = []
    for region in range(1, NR_X + 1):
        emit(f"  Region X{region}/{NR_X}")
        length = _ask_float(
            "    length [cm]", 10.0, minimum=0.0, exclusive_min=True
        )
        nodes = _ask_int("    cells", 5, minimum=3)
        XDOM.append({"length": length, "nodes": nodes})

    emit("\nY direction")
    NR_Y = _ask_int("  Number of Y regions (NR_Y)", 1, minimum=1)
    YDOM = []
    for region in range(1, NR_Y + 1):
        emit(f"  Region Y{region}/{NR_Y}")
        length = _ask_float(
            "    length [cm]", 10.0, minimum=0.0, exclusive_min=True
        )
        nodes = _ask_int("    cells", 5, minimum=3)
        YDOM.append({"length": length, "nodes": nodes})

    emit(f"\nZone map ZMAP ({NR_Y} rows x {NR_X} columns, values 1..{NZ})")

    def check_zone(value):
        if not (1 <= value <= NZ):
            raise ValueError(f"zone index must be between 1 and {NZ}, got {value}")

    ZMAP = []
    for row in range(NR_Y):
        emit(f"  Row {row + 1}/{NR_Y} (y from bottom)")
        ZMAP.append(_ask_row(f"    {NR_X} zone index(es): ", NR_X, int, check_zone))

    emit(f"\nSource map QMAP ({NR_Y} rows x {NR_X} columns, values >= 0)")

    def check_source(value):
        if value < 0:
            raise ValueError(f"source must be >= 0, got {value}")

    QMAP = []
    for row in range(NR_Y):
        emit(f"  Row {row + 1}/{NR_Y} (y from bottom)")
        QMAP.append(
            _ask_row(f"    {NR_X} source value(s): ", NR_X, float, check_source)
        )

    emit("\nBoundary conditions")
    BC = []
    for label in BC_LABELS:
        BC.append(_ask_bc(f"  {label}", 0.0))

    TOL = _ask_float(
        "Convergence tolerance (TOL)",
        1e-5,
        minimum=1e-7,
        maximum=1e-2,
    )

    solver = _ask_solver()

    config = SimulationConfig(
        N=N,
        NZ=NZ,
        zones=zones,
        NR_X=NR_X,
        XDOM=XDOM,
        NR_Y=NR_Y,
        YDOM=YDOM,
        ZMAP=ZMAP,
        QMAP=QMAP,
        BC=BC,
        TOL=TOL,
    )
    return config, solver


def print_summary(config: SimulationConfig, solver: str) -> None:
    """Print the configuration before saving it."""
    emit("\n--- 2D CONFIGURATION SUMMARY ---")
    emit(f"Quadrature order (N): {config.N}")
    emit(f"Zones (NZ): {config.NZ}")
    for index, zone in enumerate(config.zones, start=1):
        emit(
            f"  zone {index}: sigma_t={zone.sigma_t:g}, "
            f"sigma_s={zone.sigma_s:g}"
        )
    emit(
        f"X regions: {config.NR_X} "
        f"({config.total_length_x:g} cm, {config.total_nodes_x} cells)"
    )
    emit(
        f"Y regions: {config.NR_Y} "
        f"({config.total_length_y:g} cm, {config.total_nodes_y} cells)"
    )
    emit(f"Mesh: {config.total_nodes_x} x {config.total_nodes_y} cells")
    emit(f"Total source: {sum(sum(row) for row in config.QMAP):g}")
    emit(
        "Boundary conditions: "
        + ", ".join(
            f"{label}={describe_bc(value)}"
            for label, value in zip(BC_LABELS, config.BC, strict=True)
        )
    )
    emit(f"Tolerance: {config.TOL:g}")
    emit(f"Preferred solver: {solver}")


def write_config(
    config: SimulationConfig, solver: str, output: Path
) -> Path:
    """Write the validated config (plus the ``_solver`` hint) as UTF-8 JSON."""
    data = config.model_dump()
    data["_solver"] = solver
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nts-2d-config",
        description=(
            "Interactive 2D config generator; writes a JSON for "
            "nts validate / nts generate"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Output JSON path (default: auto-numbered "
            "outputs/inputs/config_2d_###.json)"
        ),
    )
    args = parser.parse_args(argv)

    try:
        config, solver = build_config_interactively()
    except Cancelled:
        emit("\nCancelled.")
        return 130
    except ValueError as exc:
        emit(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(config, solver)

    try:
        answer = _read("\nSave configuration? (y/n) [y]: ").strip().lower()
    except Cancelled:
        emit("\nCancelled.")
        return 130
    if answer == "n":
        emit("Cancelled.")
        return 0

    output = args.output or next_config_path()
    try:
        write_config(config, solver, output)
    except OSError as exc:
        emit(f"Error writing {output}: {exc}", file=sys.stderr)
        return 1

    emit(f"OK Configuration saved: {output}")
    emit(f"Next: uv run nts validate {output}")
    emit(
        f"Then: uv run nts run -s {solver} "
        f"-i <input.txt>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
