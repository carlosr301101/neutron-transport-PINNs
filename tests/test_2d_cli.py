"""Tests for the 2D CLI commands and the nts-2d-config wizard."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import generate_2d_config as wizard

ROOT = Path(__file__).resolve().parent.parent
SOLVER = ROOT / "solvers" / "runners" / "NTS_DD"

CONFIG = {
    "N": 4,
    "NZ": 1,
    "zones": [{"sigma_t": 0.5, "sigma_s": 0.3}],
    "NR_X": 1,
    "XDOM": [{"length": 10.0, "nodes": 4}],
    "NR_Y": 1,
    "YDOM": [{"length": 10.0, "nodes": 4}],
    "ZMAP": [[1]],
    "QMAP": [[1.0]],
    "BC": [-1.0, 0.0, 0.0, 0.0],
    "TOL": 1e-4,
}

WIZARD_ANSWERS = [
    "4",     # N
    "1",     # NZ
    "0.5",   # sigma_t
    "0.3",   # sigma_s
    "1",     # NR_X
    "10",    # length
    "5",     # cells
    "1",     # NR_Y
    "10",    # length
    "5",     # cells
    "1",     # ZMAP row
    "1.0",   # QMAP row
    "-1.0",  # BC left
    "0.0",   # BC bottom
    "0.0",   # BC right
    "0.0",   # BC top
    "1e-5",  # TOL
    "NTS_DD",
    "y",     # save
]


def run_cli(args, nts_home):
    """Run ``python -m cli.commands`` with an isolated work directory."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["NTS_HOME"] = str(nts_home)
    env["NTS_ASCII"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "cli.commands", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


class TestWizard(unittest.TestCase):
    def _run(self, answers, output, extra_answers=()):
        stream = list(answers) + list(extra_answers)
        stdout = io.StringIO()
        with patch("builtins.input", side_effect=stream):
            with contextlib.redirect_stdout(stdout):
                code = wizard.main(["-o", str(output)])
        return code, stdout.getvalue()

    def test_full_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(WIZARD_ANSWERS, output)
            self.assertEqual(code, 0, text)
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(data["N"], 4)
        self.assertEqual(data["BC"], [-1.0, 0.0, 0.0, 0.0])
        self.assertEqual(data["XDOM"], [{"length": 10.0, "nodes": 5}])
        self.assertEqual(data["_solver"], "NTS_DD")
        self.assertIn("Left=Reflective", text)

    def test_rows_accept_commas(self):
        answers = [
            "4", "1", "0.5", "0.3",
            "2", "10", "3", "10", "3",
            "2", "10", "3", "10", "3",
            "1,1", "1 1",          # ZMAP rows
            "1.0,0.5", "0.5 1.0",  # QMAP rows
            "0.0", "0.0", "0.0", "0.0",
            "1e-4", "NTS_DD", "y",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(answers, output)
            self.assertEqual(code, 0, text)
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["ZMAP"], [[1, 1], [1, 1]])
        self.assertEqual(data["QMAP"], [[1.0, 0.5], [0.5, 1.0]])
        self.assertEqual(len(data["XDOM"]), 2)

    def test_invalid_bc_is_retried(self):
        answers = list(WIZARD_ANSWERS)
        answers[12:16] = ["-0.5", "-1.0", "0.0", "0.0", "0.0"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(answers, output)
            self.assertEqual(code, 0, text)
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("Error:", text)
        self.assertEqual(data["BC"], [-1.0, 0.0, 0.0, 0.0])

    def test_invalid_matrix_row_is_retried(self):
        answers = list(WIZARD_ANSWERS)
        answers[10:11] = ["1 2", "1"]  # first ZMAP row has too many values
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(answers, output)
            self.assertEqual(code, 0, text)
        self.assertIn("expected 1 values", text)

    def test_odd_n_is_retried(self):
        answers = list(WIZARD_ANSWERS)
        answers[0:1] = ["5", "4"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(answers, output)
            self.assertEqual(code, 0, text)
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["N"], 4)
        self.assertIn("must be even", text)

    def test_nodes_below_three_is_retried(self):
        answers = list(WIZARD_ANSWERS)
        answers[6:7] = ["2", "3"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(answers, output)
            self.assertEqual(code, 0, text)
            data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["XDOM"][0]["nodes"], 3)
        self.assertIn("must be >= 3", text)

    def test_cancel_on_eof(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            with patch("builtins.input", side_effect=EOFError):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = wizard.main(["-o", str(output)])
        self.assertEqual(code, 130)
        self.assertFalse(output.exists())

    def test_saved_config_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "caso.json"
            code, text = self._run(WIZARD_ANSWERS, output)
            self.assertEqual(code, 0, text)
            from core.config import SimulationConfig

            config = SimulationConfig.from_json_file(str(output))
        self.assertEqual(config.BC, [-1.0, 0.0, 0.0, 0.0])


class TestCli2D(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.config_path = self.home / "caso.json"
        self.config_path.write_text(json.dumps(CONFIG), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_validate(self):
        result = run_cli(["validate", str(self.config_path)], self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Configuration is valid", result.stdout)
        self.assertIn("Left=Reflective", result.stdout)
        self.assertIn("Bottom=Vacuum", result.stdout)

    def test_validate_rejects_wrong_bc(self):
        bad = dict(CONFIG, BC=[-0.5, 0.0, 0.0, 0.0])
        bad_path = self.home / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        result = run_cli(["validate", str(bad_path)], self.home)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Validation failed", result.stdout)

    def test_generate(self):
        output = self.home / "input.txt"
        result = run_cli(
            ["generate", str(self.config_path), "-o", str(output), "-p"],
            self.home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        lines = output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 11)
        self.assertEqual(lines[-2], "-1.0 0.0 0.0 0.0")

    def test_run_dry_run(self):
        output = self.home / "input.txt"
        run_cli(["generate", str(self.config_path), "-o", str(output)], self.home)
        result = run_cli(
            ["run", "-s", "NTS_DD", "-i", str(output), "--dry-run"],
            self.home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run", result.stdout)
        self.assertIn("NTS_DD", result.stdout)
        self.assertIn("-1.0 0.0 0.0 0.0", result.stdout)

    def test_run_dry_run_missing_solver_still_prints(self):
        output = self.home / "input.txt"
        output.write_text("4\n1\n0.5 0.3\n1\n10.0 4\n1\n10.0 4\n1\n1\n0.0 0.0 0.0 0.0\n1e-4\n")
        env_dir = self.home / "empty-solvers"
        env_dir.mkdir()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["NTS_HOME"] = str(self.home)
        env["NTS_SOLVERS_DIR"] = str(env_dir)
        env["NTS_ASCII"] = "1"
        result = subprocess.run(
            [
                sys.executable, "-m", "cli.commands", "run",
                "-s", "NTS_DD", "-i", str(output), "--dry-run",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Warning", result.stdout)

    @unittest.skipUnless(SOLVER.is_file(), "NTS_DD binary not available")
    def test_run_and_show(self):
        output = self.home / "input.txt"
        run_cli(["generate", str(self.config_path), "-o", str(output)], self.home)
        result = run_cli(["run", "-s", "NTS_DD", "-i", str(output)], self.home)
        self.assertEqual(result.returncode, 0, result.stderr)

        result_file = self.home / "outputs" / "results" / "output_001.json"
        self.assertTrue(result_file.is_file())
        data = json.loads(result_file.read_text(encoding="utf-8"))
        self.assertEqual(data["STATUS"], 0)
        self.assertGreater(data["ITER"], 0)
        self.assertEqual(len(data["MFLUX"]), 4)
        self.assertEqual(len(data["MFLUX"][0]), 4)

        shown = run_cli(["show", str(result_file)], self.home)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Flux grid:", shown.stdout)
        self.assertIn("4 x 4 cells", shown.stdout)

    @unittest.skipUnless(SOLVER.is_file(), "NTS_DD binary not available")
    def test_plot_uses_physical_axes(self):
        output = self.home / "input.txt"
        run_cli(["generate", str(self.config_path), "-o", str(output)], self.home)
        run_cli(["run", "-s", "NTS_DD", "-i", str(output)], self.home)

        plot_path = self.home / "flux.png"
        result_file = self.home / "outputs" / "results" / "output_001.json"
        # Explicit input file: exercises -i.
        result = run_cli(
            ["plot", "-r", str(result_file), "-i", str(output), "-o", str(plot_path)],
            self.home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(plot_path.is_file())

    def test_show_error_result_without_flux(self):
        result_file = self.home / "error.json"
        result_file.write_text('{"STATUS": 2}', encoding="utf-8")
        shown = run_cli(["show", str(result_file)], self.home)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("Failed", shown.stdout)


if __name__ == "__main__":
    unittest.main()
