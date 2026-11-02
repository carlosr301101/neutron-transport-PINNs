"""Tests for the nts-test entry point."""

from __future__ import annotations

import unittest

from cli.run_tests import ROOT, build_suite


class TestRunTests(unittest.TestCase):
    def test_discovers_plot_tests(self):
        suite = build_suite(ROOT / "tests", "test_plot_1d_flux.py")
        self.assertGreater(suite.countTestCases(), 0)

    def test_discovers_all_tests(self):
        suite = build_suite(ROOT / "tests", "test_*.py")
        self.assertGreater(suite.countTestCases(), 10)


if __name__ == "__main__":
    unittest.main()
