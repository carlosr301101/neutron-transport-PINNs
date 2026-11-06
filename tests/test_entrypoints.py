"""Tests for the per-scheme entry points and the output metadata."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from cli.commands import cmd_run_1d
from cli.run_1d import build_parser
from solvers.runners.NTS_DD_1D import Config, Method

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
    "SPATIAL_SCHEME": "DD",
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0],
    "bound_right": [0],
    "MODE": "fixed_source",
}


def run_cli(forced, stdout: io.StringIO) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.json"
        config.write_text(json.dumps(CONFIG))
        output = Path(tmp) / "output.json"
        with contextlib.redirect_stdout(stdout):
            rc = cmd_run_1d(
                Namespace(
                    manual=False,
                    json=config,
                    config=None,
                    output=output,
                    forced_scheme=forced,
                )
            )
        if rc != 0:
            raise AssertionError(f"cmd_run_1d returned {rc}")
        return json.loads(output.read_text())


class TestEntryPointParsers(unittest.TestCase):
    def test_generic_parser_does_not_force_a_scheme(self):
        parser = build_parser()
        self.assertIsNone(parser.get_default("forced_scheme"))

    def test_scheme_parsers_force_their_scheme(self):
        self.assertEqual(build_parser(forced_scheme="DD").get_default("forced_scheme"), "DD")
        self.assertEqual(
            build_parser(forced_scheme="STEP").get_default("forced_scheme"), "STEP"
        )
        self.assertEqual(build_parser(forced_scheme="SC").get_default("forced_scheme"), "SC")


class TestForcedScheme(unittest.TestCase):
    def test_config_forces_scheme(self):
        with contextlib.redirect_stdout(io.StringIO()):
            conf = Config(manual=False, forced_scheme="SC", **CONFIG)
        self.assertEqual(conf.SPATIAL_SCHEME, "SC")
        self.assertIs(conf.method, Method.STEP_CHARACTERISTIC)

    def test_manual_wizard_skips_prompt_when_forced(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "n", "1.0", "n", "n", "0 0 0 0", "0 0 0 0",
        ]
        with patch("builtins.input", side_effect=inputs):
            with contextlib.redirect_stdout(io.StringIO()):
                conf = Config(manual=True, forced_scheme="STEP")
        self.assertEqual(conf.SPATIAL_SCHEME, "STEP")
        self.assertEqual(conf.Q.tolist(), [1.0])

    def test_cli_overrides_config_and_warns(self):
        stdout = io.StringIO()
        data = run_cli("SC", stdout)
        run = data["runs"][0]
        self.assertEqual(run["spatial_scheme"], "SC")
        self.assertEqual(data["spatial_schemes"], ["SC"])
        self.assertIn("overridden", stdout.getvalue())

    def test_cli_keeps_matching_scheme_without_warning(self):
        stdout = io.StringIO()
        data = run_cli("DD", stdout)
        self.assertEqual(data["runs"][0]["spatial_scheme"], "DD")
        self.assertEqual(data["spatial_schemes"], ["DD"])
        self.assertNotIn("overridden", stdout.getvalue())

    def test_generic_cli_uses_config_scheme(self):
        stdout = io.StringIO()
        data = run_cli(None, stdout)
        self.assertEqual(data["runs"][0]["spatial_scheme"], "DD")
        self.assertEqual(data["spatial_schemes"], ["DD"])
        self.assertNotIn("overridden", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
