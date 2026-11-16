"""Startup-cost regression tests for the TUI."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_python(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


class TestTUIStartup(unittest.TestCase):
    def test_heavy_modules_are_not_imported(self):
        result = run_python(
            "import sys; import tui.app; "
            "print(','.join(m for m in "
            "('matplotlib', 'pandas', 'openpyxl', "
            "'solvers.runners.NTS_DD_1D') if m in sys.modules))"
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_services_package_is_cheap(self):
        result = run_python(
            "import sys; import tui.services; "
            "print('tui.services.export' in sys.modules, "
            "'tui.services.plots' in sys.modules)"
        )
        self.assertEqual(result.stdout.strip(), "False False")

    def test_nts_tui_fast_path_skips_commands(self):
        result = run_python(
            "import sys; sys.argv = ['nts', 'tui']; "
            "import cli.main; import tui.app; "
            "tui.app.main = lambda: 0; "
            "print(cli.main.main(), 'cli.commands' in sys.modules)"
        )
        self.assertEqual(result.stdout.strip(), "0 False")


if __name__ == "__main__":
    unittest.main()
