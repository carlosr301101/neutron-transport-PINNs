"""Headless tests for the TUI service layer."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.placeholders import detect_placeholders
from tui.models import config_from_form, form_values_from_config, parse_field
from tui.schema import DEFAULT_CONFIG, FIELD_BY_KEY
from tui.services import config_store, export, plots, sweeps, terminal


def synthetic_payload() -> dict:
    run = {
        "config_name": "run_a",
        "mode": "eigenvalue",
        "spatial_scheme": "DD",
        "scalar_flux": [1.0, 2.0, 3.0],
        "angular_flux": [[1.0, 2.0], [1.0, 2.0], [1.0, 2.0]],
        "miu": [-0.577350269, 0.577350269],
        "omega": [1.0, 1.0],
        "iteration": 12,
        "iteration_eigenvalue": 4,
        "converged": True,
        "k_eff": 1.05,
        "k_balance": 1.050001,
        "k_history": [1.0, 1.02, 1.05],
        "configuration": {
            "num_regions": 1,
            "num_zones": 1,
            "NC": [3],
            "HR": [3.0],
            "IZL": [1],
            "SCT": [1.0],
            "SCS": [0.9],
            "NU_SIGF": [0.1],
            "Q": [0.0],
            "N": 2,
        },
    }
    return {
        "solver": "NTS_DD_1D",
        "spatial_schemes": ["DD"],
        "runs": [run],
        "total": 1,
    }


class TestFormModels(unittest.TestCase):
    def test_default_round_trip(self):
        values = form_values_from_config(copy.deepcopy(DEFAULT_CONFIG))
        config = config_from_form(values)
        self.assertEqual(config["num_regions"], 1)
        self.assertEqual(config["NC"], [1])
        self.assertEqual(config["SPATIAL_SCHEME"], "DD")

    def test_placeholder_in_list(self):
        field = FIELD_BY_KEY["NC"]
        self.assertEqual(parse_field(field, "cc, 2"), ["cc", 2])
        self.assertEqual(detect_placeholders({"NC": ["cc", 2]}), {"cc"})

    def test_placeholder_in_enum_is_ignored(self):
        self.assertEqual(
            detect_placeholders({"SPATIAL_SCHEME": "DD", "MODE": "eigenvalue"}),
            set(),
        )


class TestConfigStore(unittest.TestCase):
    def test_next_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(config_store, "INPUTS_DIR", Path(tmp)):
                first = config_store.next_config_path()
                self.assertEqual(first.name, "config_1d_001.json")
                config_store.save_config(first, copy.deepcopy(DEFAULT_CONFIG))
                second = config_store.next_config_path()
                self.assertEqual(second.name, "config_1d_002.json")
                loaded = config_store.load_config(first)
                self.assertEqual(loaded["N"], 2)

    def test_validate(self):
        errors, message = config_store.validate_config(copy.deepcopy(DEFAULT_CONFIG))
        self.assertEqual(errors, [])
        self.assertIn("valid", message)

        broken = copy.deepcopy(DEFAULT_CONFIG)
        broken["N"] = 3
        errors, _ = config_store.validate_config(broken)
        self.assertTrue(errors)

    def test_validate_placeholders_skips_fission(self):
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["SCS"] = ["kk"]
        errors, message = config_store.validate_config(config)
        self.assertEqual(errors, [])
        self.assertIn("Placeholders", message)


class TestSweeps(unittest.TestCase):
    def test_expand(self):
        base = copy.deepcopy(DEFAULT_CONFIG)
        base["SCS"] = ["kk"]
        configs = sweeps.expand_configs(base, {"kk": ("0.8", "0.9", "0.05")})
        self.assertEqual(len(configs), 3)
        self.assertEqual([config["SCS"] for config in configs], [[0.8], [0.85], [0.9]])

    def test_save_json_and_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sweep.json"
            sweeps.save_configs([copy.deepcopy(DEFAULT_CONFIG)], path)
            data = json.loads(path.read_text())
            self.assertEqual(len(data), 1)

            py_path = Path(tmp) / "sweep.py"
            sweeps.save_configs([copy.deepcopy(DEFAULT_CONFIG)], py_path)
            self.assertIn("config_dict_001", py_path.read_text())


class TestResultsAndPlots(unittest.TestCase):
    def test_summarize(self):
        from tui.services.results import summarize

        rows = summarize(synthetic_payload())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "run_a")
        self.assertAlmostEqual(rows[0]["k_eff"], 1.05)

    def test_plot_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "out.json"
            source.write_text(json.dumps(synthetic_payload()))
            for kind in ("scalar", "k-history"):
                output = plots.generate(
                    source, kind, Path(tmp) / f"{kind}.png", run_selector=["all"]
                )
                self.assertTrue(output.exists())
            angular = plots.generate(
                source,
                "angular",
                Path(tmp) / "angular.png",
                run_selector=["run_a"],
            )
            self.assertTrue(angular.exists())

    def test_excel_and_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "out.json"
            source.write_text(json.dumps(synthetic_payload()))
            workbook = export.write_excel(source, Path(tmp) / "out.xlsx")
            self.assertTrue(workbook.exists())

            datos = export.extract_positions(source, [0, 2], Path(tmp) / "datos.json")
            self.assertTrue(datos.exists())
            payload = json.loads(datos.read_text())
            self.assertEqual(payload["positions"], [0, 2])


class TestTerminal(unittest.TestCase):
    def test_protocol_detection(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(terminal.detect_image_protocol())
        with patch.dict(os.environ, {"KITTY_WINDOW_ID": "1"}, clear=True):
            self.assertEqual(terminal.detect_image_protocol(), "kitty")

    def test_positions(self):
        self.assertEqual(export.parse_positions("0, 2 4"), [0, 2, 4])
        with self.assertRaises(ValueError):
            export.parse_positions("x")
