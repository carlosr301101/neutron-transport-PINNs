#!/usr/bin/env python3
"""Entry point for `nts-test`: run the repository unittest suite."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_suite(
    start_dir: Path | None = None, pattern: str = "test_*.py"
) -> unittest.TestSuite:
    """Discover the unittest suite from <repo>/tests (or a custom directory)."""
    start = Path(start_dir) if start_dir is not None else ROOT / "tests"
    for path in (ROOT, start):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return unittest.defaultTestLoader.discover(str(start), pattern=pattern)


def run_suite(
    start_dir: Path | None = None,
    pattern: str = "test_*.py",
    verbose: bool = False,
    failfast: bool = False,
) -> int:
    """Run the suite and return 0 on success, 1 on failure."""
    suite = build_suite(start_dir, pattern)
    if suite.countTestCases() == 0:
        print(
            f"No tests matched pattern {pattern!r} in "
            f"{start_dir or ROOT / 'tests'}",
            file=sys.stderr,
        )
        return 1
    runner = unittest.TextTestRunner(
        verbosity=2 if verbose else 1,
        failfast=failfast,
    )
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nts-test",
        description="Run the NTS unittest suite",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output (verbosity=2)",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Stop at the first failure",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default="test_*.py",
        help="Test file pattern (default: test_*.py)",
    )
    parser.add_argument(
        "--start-dir",
        type=Path,
        default=None,
        help="Test directory (default: <repo>/tests)",
    )
    args = parser.parse_args(argv)

    try:
        return run_suite(
            start_dir=args.start_dir,
            pattern=args.pattern,
            verbose=args.verbose,
            failfast=args.failfast,
        )
    except Exception as exc:
        print(f"Error running tests: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
