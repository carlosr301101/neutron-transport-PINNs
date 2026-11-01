"""Tests for loading 1D configurations from JSON (--json)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from cli.commands import _load_json_configs, cmd_run_1d
from utils.extract_1d_flux import extract_flux


BENCHMARK = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [40],
    "HR": [20.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.9],
    "NU_SIGF": [0.11],
    "Q": [0.0],
    "N": 8,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0, 0, 0, 0],
    "bound_right": [0, 0, 0, 0],
    "MODE": "eigenvalue",
}


class TestJsonConfiguration(unittest.TestCase):
    def test_load_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(BENCHMARK))
            configs = _load_json_configs(path)
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0][0], "json_config_001")
        self.assertEqual(configs[0][1]["MODE"], "eigenvalue")

    def test_load_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "configs.json"
            path.write_text(json.dumps([BENCHMARK, BENCHMARK]))
            configs = _load_json_configs(path)
        self.assertEqual(len(configs), 2)
        self.assertEqual([name for name, _ in configs],
                         ["json_config_001", "json_config_002"])

    def test_load_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps([1, 2, 3]))
            with self.assertRaises(ValueError):
                _load_json_configs(path)

    def test_cmd_run_1d_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(BENCHMARK))
            output = Path(tmp) / "output.json"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_run_1d(
                    Namespace(
                        manual=False,
                        json=path,
                        config=None,
                        output=output,
                    )
                )
            self.assertEqual(rc, 0)
            data = json.loads(output.read_text())
        self.assertEqual(data["total"], 1)
        run = data["runs"][0]
        self.assertEqual(run["config_name"], "json_config_001")
        self.assertEqual(run["mode"], "eigenvalue")
        self.assertAlmostEqual(run["k_eff"], 1.0266, delta=2e-3)
        self.assertEqual(run["configuration"]["NU_SIGF"], [0.11])

    def test_extract_uses_embedded_config(self):
        payload = {
            "runs": [
                {
                    "config_name": "manual",
                    "configuration": {
                        "SCS": [0.9],
                        "NU_SIGF": [0.11],
                    },
                    "scalar_flux": [1.0, 2.0],
                    "mode": "eigenvalue",
                    "k_eff": 1.0266,
                    "k_balance": 1.0267,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "output.json"
            source.write_text(json.dumps(payload))
            missing_inputs = Path(tmp) / "missing_inputs.py"
            data = extract_flux(source, missing_inputs, [0, 1])
        rows = data["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["SCS"], 0.9)
        self.assertEqual(rows[0]["NU_SIGF"], 0.11)
        self.assertEqual(rows[0]["mode"], "eigenvalue")
        self.assertAlmostEqual(rows[0]["k_eff"], 1.0266)
        self.assertEqual(rows[0]["flux_1"], 2.0)


if __name__ == "__main__":
    unittest.main()
