#!/usr/bin/env python3
"""Extract scalar flux values at given positions from a 1D output JSON."""

import argparse
import importlib.util
import json
from pathlib import Path


def load_configs(inputs_path: Path) -> dict[str, dict]:
    if not inputs_path.exists():
        raise FileNotFoundError(f"inputs.py not found: {inputs_path}")

    spec = importlib.util.spec_from_file_location("inputs_config", inputs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module: {inputs_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return {
        name: value
        for name, value in vars(module).items()
        if isinstance(value, dict) and not name.startswith("_")
    }


def find_latest(results_dir: Path) -> Path:
    candidates = sorted(results_dir.glob("output_1d_*.json"))
    if not candidates:
        raise FileNotFoundError(f"No output_1d_*.json files in {results_dir}")
    return candidates[-1]


def parse_position(value: str) -> int:
    try:
        pos = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid position: {value}")
    if pos < 0:
        raise argparse.ArgumentTypeError(f"Position must be >= 0, got {pos}")
    return pos


def extract_flux(
    source_path: Path,
    inputs_path: Path,
    positions: list[int],
) -> dict:
    with source_path.open("r") as f:
        data = json.load(f)

    configs = load_configs(inputs_path)

    results = []
    errors = []

    for run in data.get("runs", []):
        name = run.get("config_name")
        if not name:
            errors.append("Missing config_name in run")
            continue

        cfg = configs.get(name)
        if cfg is None:
            errors.append(f"Config not found in inputs.py: {name}")
            continue

        scs_list = cfg.get("SCS")
        if not isinstance(scs_list, list) or not scs_list:
            errors.append(f"Invalid SCS for {name}")
            continue

        scalar_flux = run.get("scalar_flux") or []
        if not scalar_flux:
            errors.append(f"Empty scalar_flux for {name}")
            continue

        flux_values = {}
        for pos in positions:
            if pos < len(scalar_flux):
                flux_values[f"flux_{pos}"] = scalar_flux[pos]
            else:
                errors.append(
                    f"Position {pos} out of range for {name} (length {len(scalar_flux)})"
                )

        if len(flux_values) == len(positions):
            results.append(
                {
                    "config_name": name,
                    "SCS": scs_list[0],
                    **flux_values,
                }
            )

    payload = {
        "source": str(source_path),
        "positions": positions,
        "data": results,
    }
    if errors:
        payload["errors"] = errors

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract scalar flux at given positions from a 1D output JSON"
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to output_1d_###.json (ignored if --latest is used)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the most recent output_1d_###.json in outputs/results/",
    )
    parser.add_argument(
        "--positions",
        nargs="+",
        type=parse_position,
        default=[0, 100],
        help="Flux positions to extract (default: 0 100)",
    )
    parser.add_argument(
        "--inputs",
        default="outputs/inputs/inputs.py",
        help="Path to inputs.py (default: outputs/inputs/inputs.py)",
    )
    parser.add_argument(
        "--output",
        default="outputs/results/datos.json",
        help="Path to write datos.json (default: outputs/results/datos.json)",
    )

    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent

    if args.latest:
        source_path = find_latest(root / "outputs" / "results")
    else:
        if not args.source:
            parser.error("Provide a source path or use --latest")
        source_path = Path(args.source)
        if not source_path.is_absolute():
            source_path = root / source_path

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    inputs_path = Path(args.inputs)
    if not inputs_path.is_absolute():
        inputs_path = root / inputs_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = root / output_path

    payload = extract_flux(source_path, inputs_path, args.positions)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(payload, f, indent=2)

    print(f"✓ Datos extraídos: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
