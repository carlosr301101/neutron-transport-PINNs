"""Tests for the configuration-source line printed by the 1D runner."""

from __future__ import annotations

import contextlib
import io
import unittest

from solvers.runners.NTS_DD_1D import Config, Runner

CONFIG = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [10],
    "HR": [10.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.5],
    "NU_SIGF": [0.0],
    "Q": [1.0],
    "N": 2,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0],
    "bound_right": [0],
    "MODE": "fixed_source",
}


def build():
    with contextlib.redirect_stdout(io.StringIO()):
        return Config(manual=False, **CONFIG)


def capture(runner) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        runner()
    return buffer.getvalue()


class TestRunnerSourceLine(unittest.TestCase):
    def test_banner_without_source(self):
        output = capture(Runner(build()))
        self.assertIn("--- STARTING CALCULATION ---", output)
        self.assertNotIn("Source:", output)

    def test_banner_with_file_and_run_name(self):
        output = capture(Runner(build(), source="outputs/inputs/inputs.py", run_name="config_dict_003"))
        self.assertIn("--- STARTING CALCULATION ---", output)
        self.assertIn("Source: outputs/inputs/inputs.py | run config_dict_003", output)

    def test_banner_with_source_only(self):
        output = capture(Runner(build(), source="config.json"))
        self.assertIn("Source: config.json", output)

    def test_source_line_helper(self):
        self.assertIsNone(Runner(build())._source_line())
        self.assertEqual(
            Runner(build(), source="a.py", run_name="r1")._source_line(),
            "a.py | run r1",
        )


if __name__ == "__main__":
    unittest.main()
