#!/usr/bin/env python3
"""Interactive generator for NTS_DD_1D configuration JSON files.

The wizard asks the same questions as `nts-1d-run --manual`. In numeric
physical fields you may type a number or a placeholder name (``kk``, ``mm``,
``tt``, ...). The resulting JSON can be expanded with:

    uv run nts-generate --json config_1d_001.json \
        --place-holder kk 0.1 0.95 0.05 \
        -o outputs/inputs/inputs_1d.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solvers.runners.NTS_DD_1D import Config
from utils.paths import INPUTS_DIR


def next_config_path(base: Path | None = None) -> Path:
    """Return the next free outputs/inputs/config_1d_###.json path."""
    base = INPUTS_DIR if base is None else base
    base.mkdir(parents=True, exist_ok=True)
    existing = sorted(base.glob("config_1d_*.json"))
    if not existing:
        index = 1
    else:
        try:
            index = int(existing[-1].stem.split("_")[-1]) + 1
        except ValueError:
            index = len(existing) + 1
    return base / f"config_1d_{index:03d}.json"


def _expansion_hint(conf: Config, output: Path) -> str:
    names = sorted(conf.placeholder_names)
    parts = ["uv run", "nts-generate", "--json", str(output)]
    for name in names:
        parts += ["--place-holder", name, "START", "END", "STEP"]
    parts += ["-o", "outputs/inputs/inputs_1d.json"]
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nts-1d-generate",
        description=(
            "Interactive 1D config generator; writes a JSON for "
            "nts-1d-run --json or nts-generate --json"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Output JSON path (default: auto-numbered "
            "outputs/inputs/config_1d_###.json)"
        ),
    )
    args = parser.parse_args(argv)

    try:
        conf = Config(manual=True, allow_placeholders=True)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("\n--- RESUMEN DE LA CONFIGURACIÓN ---")
    print(conf)

    try:
        answer = input("\n¿Guardar configuración? (s/n) [s]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")
        return 130
    if answer == "n":
        print("Cancelado.")
        return 0

    output = args.output or next_config_path()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(conf.as_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    except OSError as exc:
        print(f"Error al escribir {output}: {exc}", file=sys.stderr)
        return 1

    print(f"✓ Configuración guardada: {output}")

    if conf.has_placeholders:
        print(
            "Placeholders detectados: "
            + ", ".join(sorted(conf.placeholder_names))
        )
        print("Expande con:")
        print(f"  {_expansion_hint(conf, output)}")
    else:
        print(f"Ejecuta: uv run nts-1d-run --json {output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
