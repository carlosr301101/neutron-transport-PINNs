"""Tests for the interactive manual configuration (--manual).

Run from the repository root:

    uv run python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from solvers.runners.NTS_DD_1D import Config, Runner


def run_manual(inputs: list[str]):
    with patch("builtins.input", side_effect=inputs):
        with contextlib.redirect_stdout(io.StringIO()):
            conf = Config(manual=True)
            result = Runner(conf)()
    return conf, result


class TestManualConfiguration(unittest.TestCase):
    def test_manual_eigenvalue(self):
        inputs = [
            "1", "1", "40", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "", "", "", "n", "n", "n",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "eigenvalue")
        self.assertTrue(result["k_converged"])
        self.assertAlmostEqual(result["k_eff"], 1.0266, delta=2e-3)
        self.assertEqual(conf.Q.tolist(), [0.0])
        self.assertEqual(conf.bound_left.tolist(), [0.0, 0.0, 0.0, 0.0])

    def test_manual_eigenvalue_with_power(self):
        inputs = [
            "1", "1", "40", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "", "", "",
            "s", "10", "", "", "", "2.4", "n", "n",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "eigenvalue")
        self.assertAlmostEqual(result["power_w"], 10_000.0, delta=1e-6)
        self.assertIsNotNone(result["power_scale"])
        self.assertEqual(conf.NU, 2.4)

    def test_numeric_fields_are_coerced(self):
        """Numeric prompts must yield float/int, never str or None."""
        inputs = [
            "1", "1", "40", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "", "", "",
            "s", "10", "", "", "", "2.4", "n", "n",
        ]
        conf, _ = run_manual(inputs)
        self.assertIsInstance(conf.TOL_K, float)
        self.assertIsInstance(conf.MAX_OUTER, int)
        self.assertIsInstance(conf.POWER_KW, float)
        self.assertIsInstance(conf.E_F_MEV, float)
        self.assertIsInstance(conf.AREA_CM2, float)
        self.assertIsInstance(conf.NU, float)
        self.assertIsInstance(conf.N, int)
        self.assertIsInstance(conf.N_HALF, int)

    def test_k0_is_coerced_to_float(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "", "", "1.1", "n", "n", "n",
        ]
        conf, _ = run_manual(inputs)
        self.assertIsInstance(conf.K0, float)
        self.assertAlmostEqual(conf.K0, 1.1)

    def test_placeholder_rejected_in_numeric_field(self):
        """TOL_K and friends are numeric-only even in generator mode."""
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "kk",
        ]
        with self.assertRaises(ValueError):
            with patch("builtins.input", side_effect=inputs):
                with contextlib.redirect_stdout(io.StringIO()):
                    Config(manual=True, allow_placeholders=True)

    def test_manual_eigenvalue_with_sigma_f_power(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.5",
            "", "", "s", "0.3", "eigenvalue", "", "", "",
            "s", "10", "", "", "sigma_f", "0.3", "s", "s",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "eigenvalue")
        self.assertAlmostEqual(result["power_w"], 10_000.0, delta=1e-6)
        self.assertEqual(conf.SIGMA_F.tolist(), [0.3])

    def test_manual_fixed_k_with_source(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.05", "fixed_k", "1.0", "", "", "",
            "n", "1.0", "s", "s",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "fixed_k")
        self.assertEqual(result["k_eff"], 1.0)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["k_balance"], 0.5, delta=1e-4)

    def test_manual_driven(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.05", "driven", "", "", "",
            "n", "1.0", "n", "n", "0 0 0 0", "0 0 0 0",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "driven")
        self.assertEqual(result["k_eff"], 1.0)
        self.assertTrue(result["converged"])
        self.assertLess(result["k_balance"], 1.0)

    def test_manual_driven_without_source_fails(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.05", "driven", "", "", "",
            "n", "0", "n", "n", "0 0 0 0", "0 0 0 0",
        ]
        with self.assertRaises(ValueError):
            run_manual(inputs)

    def test_manual_fixed_source(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "n", "1", "s", "s",
        ]
        conf, result = run_manual(inputs)
        self.assertEqual(result["mode"], "fixed_source")
        self.assertIsNone(result["k_eff"])
        self.assertTrue(result["converged"])

    def test_manual_invalid_mode(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.1", "foo",
        ]
        with self.assertRaises(ValueError):
            run_manual(inputs)

    def test_as_dict_is_json_serializable(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "", "s", "0.3", "eigenvalue", "", "", "", "n", "s", "s",
        ]
        conf, _ = run_manual(inputs)
        payload = conf.as_dict()
        self.assertEqual(payload["MODE"], "eigenvalue")
        self.assertEqual(payload["NU_SIGF"], [0.3])
        self.assertEqual(payload["N"], 8)
        json.dumps(payload)  # must not raise

    def test_cmd_run_1d_manual(self):
        from cli.commands import cmd_run_1d

        inputs = [
            "1", "1", "40", "20", "1", "1.0", "0.9",
            "", "", "s", "0.11", "eigenvalue", "", "", "", "n", "n", "n",
            "s",  # confirm execution
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "manual.json"
            with patch("builtins.input", side_effect=inputs):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = cmd_run_1d(
                        Namespace(
                            manual=True,
                            json=None,
                            config=None,
                            output=output,
                        )
                    )
            self.assertEqual(rc, 0)
            data = json.loads(output.read_text())
            self.assertEqual(data["total"], 1)
            run = data["runs"][0]
            self.assertEqual(run["config_name"], "manual")
            self.assertEqual(run["mode"], "eigenvalue")
            self.assertAlmostEqual(run["k_eff"], 1.0266, delta=2e-3)
            self.assertIn("configuration", run)


if __name__ == "__main__":
    unittest.main()
