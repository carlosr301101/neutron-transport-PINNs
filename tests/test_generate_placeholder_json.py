"""Tests for nts-generate --json (JSON placeholder expansion)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from cli.commands import cmd_generate_placeholder


BASE = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [40],
    "HR": [20.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": ["kk"],
    "NU_SIGF": ["mm"],
    "SIGMA_F": None,
    "Q": [0.0],
    "N": 8,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0.0, 0.0, 0.0, 0.0],
    "bound_right": [0.0, 0.0, 0.0, 0.0],
    "MODE": "eigenvalue",
    "K_EFF": None,
    "TOL_K": 1e-6,
    "MAX_OUTER": 200,
    "K0": None,
    "POWER_KW": None,
    "E_F_MEV": 200.0,
    "NU": None,
    "AREA_CM2": 1.0,
}


def write_config(path: Path) -> None:
    path.write_text(json.dumps(BASE))


class TestGeneratePlaceholderJson(unittest.TestCase):
    def test_expand_to_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "config_1d_001.json"
            out = Path(tmp) / "inputs_1d.json"
            write_config(src)
            args = Namespace(
                place_holder=[
                    ("kk", "0.1", "0.5", "0.2"),
                    ("mm", "0.05", "0.15", "0.05"),
                ],
                json=src,
                output=out,
                config=None,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_generate_placeholder(args)
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text())
        self.assertEqual(len(data), 3)
        self.assertEqual([cfg["SCS"][0] for cfg in data], [0.1, 0.3, 0.5])
        self.assertEqual(
            [cfg["NU_SIGF"][0] for cfg in data], [0.05, 0.1, 0.15]
        )
        self.assertEqual(data[0]["TOL_K"], 1e-6)
        self.assertEqual(data[0]["MODE"], "eigenvalue")

    def test_expand_to_inputs_py(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "config_1d_001.json"
            out = Path(tmp) / "inputs.py"
            write_config(src)
            args = Namespace(
                place_holder=[
                    ("kk", "0.1", "0.3", "0.2"),
                    ("mm", "0.05", "0.10", "0.05"),
                ],
                json=src,
                output=out,
                config=None,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_generate_placeholder(args)
            self.assertEqual(rc, 0)
            text = out.read_text()
        self.assertIn("config_dict_001", text)
        self.assertIn("config_dict_002", text)
        self.assertIn("1e-06", text)

    def test_missing_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "config_1d_001.json"
            out = Path(tmp) / "inputs_1d.json"
            write_config(src)
            args = Namespace(
                place_holder=[("kk", "0.1", "0.5", "0.2")],
                json=src,
                output=out,
                config=None,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_generate_placeholder(args)
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_load_json_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "configs.json"
            out = Path(tmp) / "inputs_1d.json"
            src.write_text(json.dumps([BASE, BASE]))
            args = Namespace(
                place_holder=[
                    ("kk", "0.1", "0.2", "0.1"),
                    ("mm", "0.05", "0.10", "0.05"),
                ],
                json=src,
                output=out,
                config=None,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_generate_placeholder(args)
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text())
        self.assertEqual(len(data), 4)


if __name__ == "__main__":
    unittest.main()
