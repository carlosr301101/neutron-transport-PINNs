#!/usr/bin/env python3
"""Compatibility shim for the CLI entry point.

The implementation lives in :mod:`cli.main`; this file keeps
``python main.py ...`` working for older workflows.
"""

from cli.main import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
