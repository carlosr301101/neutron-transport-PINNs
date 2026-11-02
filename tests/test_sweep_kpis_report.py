"""Regression test: sweep_kpis reports use English labels."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "nts-pinns-autopilot" / "scripts" / "sweep_kpis.py"


class TestSweepKpisReport(unittest.TestCase):
    def test_report_is_english(self):
        payload = {
            "runs": [
                {
                    "config_name": "config_dict_001",
                    "configuration": {"SCS": [0.1]},
                    "scalar_flux": [1.0, 0.5],
                    "iteration": 9,
                    "converged": True,
                    "k_eff": 1.02,
                    "k_balance": 1.02,
                },
                {
                    "config_name": "config_dict_002",
                    "configuration": {"SCS": [0.2]},
                    "scalar_flux": [0.9, 0.4],
                    "iteration": 12,
                    "converged": True,
                    "k_eff": 1.03,
                    "k_balance": 1.03,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "output_1d_N4.json"
            source.write_text(json.dumps(payload))
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(source),
                    "--positions",
                    "0",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("iterations", result.stdout)
        self.assertNotIn("iteraciones", result.stdout)
        self.assertIn("## Validated runs", result.stdout)
        self.assertIn("## k_eff", result.stdout)


if __name__ == "__main__":
    unittest.main()
