#!/usr/bin/env python3
"""Entry point for `nts-1d-run`."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cli() -> int:
    from cli.commands import cmd_run_1d

    parser = argparse.ArgumentParser(prog="nts-1d-run", add_help=True)
    parser.add_argument(
        "-c",
        "--config",
        default="outputs/inputs/inputs.py",
        help="Path to inputs.py file (default: outputs/inputs/inputs.py)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path (default: outputs/results/output_1d_###.json)",
    )
    args = parser.parse_args()

    return cmd_run_1d(args)


if __name__ == "__main__":
    raise SystemExit(cli())
