#!/usr/bin/env python3
"""Entry points for the 1D S_N solver.

``nts-1d-run`` uses the scheme stored in the configuration (default ``DD``),
while ``nts-1d-run-dd``, ``nts-1d-run-step`` and ``nts-1d-run-sc`` force
their scheme regardless of what the configuration says.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_parser(
    prog: str = "nts-1d-run", forced_scheme: str | None = None
) -> argparse.ArgumentParser:
    """Build the shared argparse parser for every 1D run entry point."""
    parser = argparse.ArgumentParser(prog=prog, add_help=True)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "-c",
        "--config",
        default="outputs/inputs/inputs.py",
        help="Path to inputs.py or a JSON config (default: outputs/inputs/inputs.py)",
    )
    source.add_argument(
        "--json",
        type=Path,
        help="Path to a JSON config object or list of objects",
    )
    source.add_argument(
        "--manual",
        action="store_true",
        help="Interactive step-by-step configuration",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path (default: auto-numbered outputs/results/output_1d_###.json)",
    )
    parser.set_defaults(forced_scheme=forced_scheme)
    return parser


def _run(prog: str, forced_scheme: str | None) -> int:
    from cli.commands import cmd_run_1d

    args = build_parser(prog, forced_scheme).parse_args()
    return cmd_run_1d(args)


def cli() -> int:
    """Scheme comes from the configuration (default DD)."""
    return _run("nts-1d-run", None)


def cli_dd() -> int:
    """Force the Diamond Difference scheme."""
    return _run("nts-1d-run-dd", "DD")


def cli_step() -> int:
    """Force the Step scheme."""
    return _run("nts-1d-run-step", "STEP")


def cli_sc() -> int:
    """Force the Step Characteristic scheme."""
    return _run("nts-1d-run-sc", "SC")


if __name__ == "__main__":
    raise SystemExit(cli())
