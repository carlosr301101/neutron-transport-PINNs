#!/usr/bin/env python3
"""Entry point for `nts-generate` (placeholder mode)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cli() -> int:
    from cli.commands import cmd_generate

    parser = argparse.ArgumentParser(prog="nts-generate", add_help=True)
    parser.add_argument(
        "--place-holder",
        nargs=4,
        action="append",
        metavar=("NAME", "START", "END", "STEP"),
        help="Generate outputs/inputs/inputs.py from inputs_placeholder.py",
    )
    args = parser.parse_args()

    return cmd_generate(args)


if __name__ == "__main__":
    raise SystemExit(cli())
