"""Tests for the nts-1d-generate interactive configuration generator."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from solvers.runners.NTS_DD_1D import Config
from utils import generate_1d_config as gen


CONCRETE = [
    "1", "1", "40", "20", "1", "1.0", "0.9",
    "", "s", "0.11", "eigenvalue", "", "", "", "n", "n", "n", "s",
]
PLACEHOLDER = [
    "1", "1", "40", "20", "1", "1.0", "kk",
    "", "s", "mm", "eigenvalue", "", "", "", "n", "n", "n", "s",
]


class TestGenerate1DConfig(unittest.TestCase):
    def test_concrete_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "config.json"
            with patch("builtins.input", side_effect=CONCRETE):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = gen.main(["-o", str(output)])
            self.assertEqual(rc, 0)
            data = json.loads(output.read_text())
        self.assertEqual(data["MODE"], "eigenvalue")
        self.assertEqual(data["SCS"], [0.9])
        self.assertEqual(data["NU_SIGF"], [0.11])
        self.assertEqual(data["TOL_K"], 1e-6)
        with contextlib.redirect_stdout(io.StringIO()):
            conf = Config(manual=False, **data)
        self.assertEqual(conf.N, 8)
        self.assertEqual(conf.NTC, 40)

    def test_placeholder_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "config.json"
            with patch("builtins.input", side_effect=PLACEHOLDER):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = gen.main(["-o", str(output)])
            self.assertEqual(rc, 0)
            data = json.loads(output.read_text())
        self.assertEqual(data["SCS"], ["kk"])
        self.assertEqual(data["NU_SIGF"], ["mm"])
        self.assertEqual(data["TOL_K"], 1e-6)

    def test_invalid_numeric_value(self):
        bad = [
            "1", "1", "40", "20", "1", "1.0", "abc def",
            "", "s", "0.11", "eigenvalue", "", "", "", "n", "n", "n", "s",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "config.json"
            with patch("builtins.input", side_effect=bad):
                with contextlib.redirect_stdout(io.StringIO()):
                    with contextlib.redirect_stderr(io.StringIO()):
                        rc = gen.main(["-o", str(output)])
            self.assertEqual(rc, 1)
            self.assertFalse(output.exists())

    def test_next_config_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "config_1d_001.json").write_text("{}")
            self.assertEqual(
                gen.next_config_path(base).name, "config_1d_002.json"
            )
            (base / "config_1d_007.json").write_text("{}")
            self.assertEqual(
                gen.next_config_path(base).name, "config_1d_008.json"
            )

    def test_auto_numbered_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gen, "INPUTS_DIR", Path(tmp)):
                with patch("builtins.input", side_effect=CONCRETE):
                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = gen.main([])
                self.assertEqual(rc, 0)
                self.assertTrue((Path(tmp) / "config_1d_001.json").exists())
                with patch("builtins.input", side_effect=CONCRETE):
                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = gen.main([])
                self.assertEqual(rc, 0)
                self.assertTrue((Path(tmp) / "config_1d_002.json").exists())


if __name__ == "__main__":
    unittest.main()
