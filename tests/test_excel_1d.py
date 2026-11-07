"""Tests for the Excel export (`nts-1d-excel` and `nts-1d-run --excel`)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import openpyxl

from cli.commands import cmd_run_1d
from utils import excel_1d

CONFIG_A = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [4],
    "HR": [4.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.5],
    "NU_SIGF": [0.0],
    "Q": [1.0],
    "N": 2,
    "SPATIAL_SCHEME": "DD",
    "MODE": "fixed_source",
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [1.0],
    "bound_right": [0.0],
}

CONFIG_B = {
    **CONFIG_A,
    "NC": [3],
    "SPATIAL_SCHEME": "SC",
    "NU_SIGF": [0.1],
    "MODE": "eigenvalue",
    "Q": [0.0],
    "bound_left": [0.0],
}

RUN_A = {
    "config_name": "run_a",
    "configuration": CONFIG_A,
    "scalar_flux": [1.0, 0.8, 0.6, 0.4],
    "angular_flux": [[0.9, 1.1], [0.7, 0.9], [0.5, 0.7], [0.3, 0.5]],
    "miu": [-0.57735, 0.57735],
    "omega": [1.0, 1.0],
    "iteration": 12,
    "converged": True,
    "mode": "fixed_source",
    "spatial_scheme": "DD",
    "k_eff": None,
    "k_balance": None,
    "k_history": [],
    "k_converged": None,
    "outer_iterations": 0,
    "power_w": None,
    "power_scale": 1.0,
    "source": "a.json",
    "timestamp": "2026-11-07T00:00:01",
}

RUN_B = {
    "config_name": "run_b",
    "configuration": CONFIG_B,
    "scalar_flux": [0.2, 0.5, 0.2],
    "angular_flux": [[0.1, 0.3], [0.4, 0.6], [0.2, 0.2]],
    "miu": [-0.57735, 0.57735],
    "omega": [1.0, 1.0],
    "iteration": 40,
    "converged": True,
    "mode": "eigenvalue",
    "spatial_scheme": "SC",
    "k_eff": 1.026676,
    "k_balance": 1.026677,
    "k_history": [1.1, 1.05],
    "k_converged": True,
    "outer_iterations": 2,
    "power_w": 10000.0,
    "power_scale": 12.5,
    "source": "b.json",
    "timestamp": "2026-11-07T00:00:02",
}

PAYLOAD = {
    "solver": "NTS_DD_1D",
    "spatial_schemes": ["DD", "SC"],
    "runs": [RUN_A, RUN_B],
    "total": 2,
    "failures": 0,
    "generated_at": "2026-11-07T00:00:00",
}

SHEETS = [
    "Metadata",
    "Runs",
    "Zones",
    "Regions",
    "Boundaries",
    "ScalarFlux",
    "AngularFlux",
    "Directions",
    "k_history",
]


def write_payload(tmp: str) -> Path:
    source = Path(tmp) / "output_1d_001.json"
    source.write_text(json.dumps(PAYLOAD))
    return source


def header(worksheet) -> list:
    return [cell.value for cell in worksheet[1]]


class TestExcelWorkbook(unittest.TestCase):
    def test_sheets_and_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.xlsx"
            excel_1d.write_workbook(PAYLOAD, output)
            wb = openpyxl.load_workbook(output)

        self.assertEqual(wb.sheetnames, SHEETS)

        metadata = dict(wb["Metadata"].iter_rows(min_row=2, values_only=True))
        self.assertEqual(metadata["solver"], "NTS_DD_1D")
        self.assertEqual(metadata["total"], 2)
        self.assertEqual(metadata["spatial_schemes"], "DD, SC")

        runs = wb["Runs"]
        self.assertEqual(runs.max_row, 3)
        self.assertEqual(header(runs)[0], "run")
        self.assertEqual(runs["A2"].value, "run_a")
        self.assertEqual(runs["D3"].value, 1.026676)

        scalar = wb["ScalarFlux"]
        self.assertEqual(header(scalar), ["cell", "run_a", "run_b"])
        self.assertEqual(scalar.max_row, 5)  # 4 cells + header
        self.assertEqual(scalar["B2"].value, 1.0)
        self.assertIsNone(scalar["C5"].value)  # run_b has only 3 cells

        angular = wb["AngularFlux"]
        self.assertEqual(header(angular), ["run", "cell", "x_cm", "direction", "mu", "psi"])
        self.assertEqual(angular.max_row, 1 + 4 * 2 + 3 * 2)

        self.assertEqual(wb["Directions"].max_row, 5)
        self.assertEqual(wb["k_history"].max_row, 3)
        self.assertEqual(wb["Zones"].max_row, 3)
        self.assertEqual(wb["Regions"].max_row, 3)

    def test_header_style_and_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.xlsx"
            excel_1d.write_workbook(PAYLOAD, output)
            wb = openpyxl.load_workbook(output)
        ws = wb["Runs"]
        self.assertTrue(ws["A1"].font.bold)
        self.assertEqual(ws.freeze_panes, "A2")
        self.assertEqual(ws.auto_filter.ref, "A1:N3")

    def test_run_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write_payload(tmp)
            output = Path(tmp) / "filtered.xlsx"
            rc = excel_1d.main(
                [str(source), "-o", str(output), "--run", "run_b"]
            )
            wb = openpyxl.load_workbook(output)
        self.assertEqual(rc, 0)
        self.assertEqual(wb["Runs"].max_row, 2)
        self.assertEqual(wb["Runs"]["A2"].value, "run_b")
        self.assertEqual(header(wb["ScalarFlux"]), ["cell", "run_b"])

    def test_default_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write_payload(tmp)
            rc = excel_1d.main([str(source)])
            output = source.with_suffix(".xlsx")
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_invalid_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            source.write_text(json.dumps([1, 2, 3]))
            with contextlib.redirect_stderr(io.StringIO()):
                rc = excel_1d.main([str(source)])
        self.assertEqual(rc, 1)

    def test_unknown_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write_payload(tmp)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = excel_1d.main([str(source), "--run", "nope"])
        self.assertEqual(rc, 2)

    def test_legacy_run_without_directions(self):
        legacy = dict(RUN_A)
        legacy.pop("miu")
        legacy.pop("omega")
        payload = {**PAYLOAD, "runs": [legacy], "total": 1}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "legacy.xlsx"
            excel_1d.write_workbook(payload, output)
            wb = openpyxl.load_workbook(output)
        self.assertIn("AngularFlux", wb.sheetnames)
        self.assertIsNone(wb["AngularFlux"]["E2"].value)  # mu is None
        self.assertEqual(wb["Directions"].max_row, 1)  # header only


class TestRunExcelFlag(unittest.TestCase):
    def _run(self, excel) -> tuple[Path, Path]:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(json.dumps(CONFIG_A))
            output = Path(tmp) / "output.json"
            excel_path = Path(tmp) / "custom.xlsx"
            target = str(excel_path) if excel == "custom" else excel
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_run_1d(
                    Namespace(
                        manual=False,
                        json=config,
                        config=None,
                        output=output,
                        forced_scheme=None,
                        excel=target,
                    )
                )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())
            expected = (
                output.with_suffix(".xlsx") if excel == "auto" else excel_path
            )
            self.assertTrue(expected.exists())
            wb = openpyxl.load_workbook(expected)
            self.assertEqual(wb.sheetnames, SHEETS)
            return output, expected

    def test_auto_path(self):
        self._run("auto")

    def test_explicit_path(self):
        self._run("custom")


if __name__ == "__main__":
    unittest.main()
