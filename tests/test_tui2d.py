"""Tests for the 2D TUI, its services and the entry point."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from textual.widgets import DataTable, Input, Select, Static, TabbedContent

from tui2d.app import NTS2DApp
from tui2d.screens import Config2DPane, Plots2DPane, Results2DPane, Run2DPane
from tui2d.services import results as results_service
from tui2d.services import plots as plots_service
from tui2d.services.runner import RunOutcome, SolverRunner
from tui2d.widgets import BCTable, DomainMap, MatrixEditor, RegionTable, ZoneTable
from utils.paths import get_solver_path

ROOT = Path(__file__).resolve().parents[1]


def small_config() -> dict:
    return {
        "N": 4,
        "NZ": 1,
        "zones": [{"sigma_t": 0.5, "sigma_s": 0.3}],
        "NR_X": 1,
        "XDOM": [{"length": 10.0, "nodes": 5}],
        "NR_Y": 1,
        "YDOM": [{"length": 10.0, "nodes": 5}],
        "ZMAP": [[1]],
        "QMAP": [[1.0]],
        "BC": [0.0, 0.0, 0.0, 0.0],
        "TOL": 1e-4,
    }


class TestTUI2DApp(unittest.IsolatedAsyncioTestCase):
    async def test_mount_and_tabs(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            self.assertEqual(tabs.active, "tab2d-dashboard")
            for tab in (
                "tab2d-dashboard",
                "tab2d-config",
                "tab2d-run",
                "tab2d-results",
                "tab2d-plots",
            ):
                tabs.active = tab
                await pilot.pause()
                self.assertEqual(tabs.active, tab)

    async def test_default_form_and_preview(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            self.assertEqual(pane.query_one("#cfg2d-N", Select).value, "4")
            self.assertEqual(pane.query_one("#cfg2d-solver", Select).value, "NTS_DD")
            config = pane.collect_config()
            self.assertEqual(config["NR_X"], 1)
            self.assertEqual(config["NR_Y"], 1)
            self.assertEqual(config["ZMAP"], [[1]])
            preview = pane.query_one("#cfg2d-preview", Static).content
            self.assertEqual(len(str(preview).strip().splitlines()), 11)

    async def test_domain_map_is_proportional(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            domain = pane.query_one("#cfg2d-domain", DomainMap)

            # 20 x 10 cm: twice as wide as tall in physical terms, and the
            # drawing compensates the terminal cell aspect ratio.
            pane.query_one("#xregion-table", RegionTable).set_rows(
                [{"length": 20.0, "cells": 10}]
            )
            pane.query_one("#yregion-table", RegionTable).set_rows(
                [{"length": 10.0, "cells": 5}]
            )
            pane._refresh_all()
            await pilot.pause()
            self.assertGreater(domain.last_cols, domain.last_rows)
            self.assertAlmostEqual(
                domain.last_rows / domain.last_cols,
                domain.last_ratio * 0.5,
                delta=0.03,
            )

            # 10 x 20 cm: taller than wide.
            pane.query_one("#xregion-table", RegionTable).set_rows(
                [{"length": 10.0, "cells": 5}]
            )
            pane.query_one("#yregion-table", RegionTable).set_rows(
                [{"length": 20.0, "cells": 10}]
            )
            pane._refresh_all()
            await pilot.pause()
            self.assertGreater(domain.last_rows, domain.last_cols // 2)
            self.assertAlmostEqual(
                domain.last_rows / domain.last_cols,
                domain.last_ratio * 0.5,
                delta=0.03,
            )

            # The legend and axes are part of the rendered text.
            self.assertIn("X: 10 cm", domain.last_plain)
            self.assertIn("Y: 20 cm", domain.last_plain)
            self.assertIn("BC:", domain.last_plain)

    async def test_region_rows_resize_matrices(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            pane.query_one("#xregion-table", RegionTable).set_rows(
                [
                    {"length": 5.0, "cells": 3},
                    {"length": 5.0, "cells": 3},
                ]
            )
            pane.query_one("#yregion-table", RegionTable).set_rows(
                [{"length": 5.0, "cells": 3}, {"length": 5.0, "cells": 3}]
            )
            pane._refresh_all()
            await pilot.pause()
            zmap = pane.query_one("#cfg2d-zmap", MatrixEditor)
            qmap = pane.query_one("#cfg2d-qmap", MatrixEditor)
            self.assertEqual((zmap.rows, zmap.cols), (2, 2))
            self.assertEqual((qmap.rows, qmap.cols), (2, 2))
            config = pane.collect_config()
            self.assertEqual(config["NR_X"], 2)
            self.assertEqual(config["NR_Y"], 2)
            self.assertEqual(len(config["ZMAP"]), 2)
            self.assertEqual(len(config["ZMAP"][0]), 2)

    async def test_matrix_editors_shrink_to_content(self):
        app = NTS2DApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            zmap = pane.query_one("#cfg2d-zmap", MatrixEditor)
            qmap = pane.query_one("#cfg2d-qmap", MatrixEditor)
            # A Vertical defaults to 1fr; without height:auto the editor would
            # grow to the whole viewport and leave a large gap before QMAP.
            self.assertLess(zmap.size.height, 12)
            self.assertLess(qmap.size.height, 12)
            gap = qmap.region.y - (zmap.region.y + zmap.size.height)
            self.assertLess(gap, 10)

    async def test_bc_table_round_trip(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            table = pane.query_one(BCTable)
            table.set_values([-1.0, 0.0, 2.5, 0.0])
            await pilot.pause()
            self.assertEqual(table.values(), [-1.0, 0.0, 2.5, 0.0])

            pane.query_one("#bc-left-type", Select).value = "incoming"
            await pilot.pause()
            pane.query_one("#bc-left-value", Input).value = "3.0"
            await pilot.pause()
            self.assertEqual(table.values()[0], 3.0)
            self.assertIn("Incoming", pane.query_one("#cfg2d-domain").last_plain)

    async def test_save_and_load_round_trip(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            pane.query_one(ZoneTable).set_rows(
                [{"name": "Core", "sigma_t": 1.0, "sigma_s": 0.8}]
            )
            pane.query_one("#cfg2d-zmap", MatrixEditor).set_values([[1]])
            pane.query_one("#cfg2d-qmap", MatrixEditor).set_values([[2.5]])
            pane.query_one(BCTable).set_values([-1.0, 0.0, 1.0, 0.0])
            await pilot.pause()

            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "config_2d.json"
                saved = pane.save_current(path)
                self.assertEqual(saved, path)
                data = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(data["zones"], [{"sigma_t": 1.0, "sigma_s": 0.8}])
            self.assertEqual(data["ZONE_NAMES"], ["Core"])
            self.assertEqual(data["QMAP"], [[2.5]])
            self.assertEqual(data["BC"], [-1.0, 0.0, 1.0, 0.0])
            self.assertEqual(data["_solver"], "NTS_DD")

            pane.populate(data)
            await pilot.pause()
            self.assertEqual(pane.collect_config()["BC"], [-1.0, 0.0, 1.0, 0.0])
            self.assertEqual(pane.query_one("#zone-0-name", Input).value, "Core")

    async def test_validation_reports_bad_cells(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-config"
            await pilot.pause()
            pane = app.query_one(Config2DPane)
            pane.query_one("#xregion-table", RegionTable).set_rows(
                [{"length": 10.0, "cells": 1}]
            )
            pane._refresh_all()
            pane.validate_current()
            await pilot.pause()
            status = str(pane.query_one("#cfg2d-status", Static).content).lower()
            self.assertIn("invalid", status)

    async def test_results_table_and_detail(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-results"
            await pilot.pause()
            pane = app.query_one(Results2DPane)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "output_001.json"
                out.write_text(
                    json.dumps(
                        {
                            "STATUS": 0,
                            "ITER": 7,
                            "CPU": 0.01,
                            "MFLUX": [[1.0, 2.0], [3.0, 4.0]],
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.object(results_service, "RESULTS_DIR", Path(tmp)):
                    pane.refresh_outputs()
                    await pilot.pause()
                    table = pane.query_one("#res2d-table", DataTable)
                    self.assertEqual(table.row_count, 1)
                    row = table.get_row_at(0)
                    self.assertEqual(row[0], "0")
                    self.assertEqual(row[1], "7")
                    self.assertEqual(row[3], "2x2")

    async def test_plots_pane_source(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            pane = app.query_one(Plots2DPane)
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "output_002.json"
                out.write_text(
                    json.dumps(
                        {
                            "STATUS": 0,
                            "ITER": 3,
                            "CPU": 0.001,
                            "MFLUX": [[1.0]],
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.object(results_service, "RESULTS_DIR", Path(tmp)):
                    pane.set_source(out)
                    await pilot.pause()
                    self.assertEqual(
                        str(pane.query_one("#plot2d-result", Select).value), str(out)
                    )

    async def test_plots_selects_the_newest_result(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            pane = app.query_one(Plots2DPane)
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                for name in ("output_001.json", "output_002.json"):
                    (tmp / name).write_text(
                        json.dumps({"STATUS": 0, "MFLUX": [[1.0]]}),
                        encoding="utf-8",
                    )
                with patch.object(results_service, "RESULTS_DIR", tmp):
                    pane.refresh_results()
                    await pilot.pause()
                    select = pane.query_one("#plot2d-result", Select)
                    self.assertEqual(
                        str(select.value), str(tmp / "output_002.json")
                    )

                    # A new result from a run becomes the selected one.
                    (tmp / "output_003.json").write_text(
                        json.dumps({"STATUS": 0, "MFLUX": [[2.0]]}),
                        encoding="utf-8",
                    )
                    pane.refresh_results()
                    await pilot.pause()
                    self.assertEqual(
                        str(select.value), str(tmp / "output_003.json")
                    )

    async def test_plots_accepts_a_manual_path(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            pane = app.query_one(Plots2DPane)
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                external = tmp / "elsewhere.json"
                external.write_text(
                    json.dumps({"STATUS": 0, "MFLUX": [[1.0]]}),
                    encoding="utf-8",
                )
                with patch.object(
                    results_service, "RESULTS_DIR", tmp / "empty"
                ):
                    pane.query_one("#plot2d-path", Input).value = str(external)
                    pane.on_button_pressed(
                        SimpleNamespace(
                            button=SimpleNamespace(id="plot2d-load-path")
                        )
                    )
                    await pilot.pause()
                    self.assertEqual(
                        str(pane.query_one("#plot2d-result", Select).value),
                        str(external),
                    )

    async def test_use_in_plots_switches_and_selects(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-results"
            await pilot.pause()
            pane = app.query_one(Results2DPane)
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                out = tmp / "output_042.json"
                out.write_text(
                    json.dumps({"STATUS": 0, "ITER": 1, "MFLUX": [[1.0]]}),
                    encoding="utf-8",
                )
                with patch.object(results_service, "RESULTS_DIR", tmp):
                    pane.refresh_outputs()
                    await pilot.pause()
                    pane.on_button_pressed(
                        SimpleNamespace(
                            button=SimpleNamespace(id="res2d-to-plots")
                        )
                    )
                    await pilot.pause()
                    self.assertEqual(
                        app.query_one("#tabs", TabbedContent).active,
                        "tab2d-plots",
                    )
                    self.assertEqual(
                        str(
                            app.query_one(Plots2DPane)
                            .query_one("#plot2d-result", Select)
                            .value
                        ),
                        str(out),
                    )

    async def test_run_finish_shows_output_path(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-run"
            await pilot.pause()
            pane = app.query_one(Run2DPane)
            outcome = RunOutcome(
                config=Path("config_2d_001.json"),
                input=Path("outputs/inputs/input_010.txt"),
                output=Path("outputs/results/output_010.json"),
                status=0,
                iterations=19,
                cpu=0.000584,
            )
            pane._finish([outcome])
            await pilot.pause()
            shown = str(pane.query_one("#run2d-output", Static).content)
            self.assertIn("output_010.json", shown)
            self.assertFalse(pane.query_one("#run2d-plots").disabled)
            self.assertFalse(pane.query_one("#run2d-results").disabled)
            self.assertIn(
                "output_010.json", Run2DPane._status_text([outcome])
            )

    async def test_run_pane_exposes_cancel(self):
        app = NTS2DApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab2d-run"
            await pilot.pause()
            pane = app.query_one(Run2DPane)
            self.assertTrue(pane.query_one("#run2d-cancel").disabled)
            self.assertFalse(pane.query_one("#run2d-start").disabled)
            self.assertTrue(pane.query_one("#run2d-results").disabled)
            self.assertTrue(pane.query_one("#run2d-plots").disabled)


class TestServices(unittest.TestCase):
    def test_plots_service_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            input_path = tmp / "input_001.txt"
            input_path.write_text(
                "\n".join(
                    [
                        "4",
                        "1",
                        "0.5 0.3",
                        "1",
                        "10.0 2",
                        "1",
                        "10.0 2",
                        "1",
                        "1.0",
                        "0.0 0.0 0.0 0.0",
                        "1e-4",
                    ]
                ),
                encoding="utf-8",
            )
            result_path = tmp / "output_001.json"
            result_path.write_text(
                json.dumps(
                    {
                        "STATUS": 0,
                        "ITER": 4,
                        "CPU": 0.001,
                        "MFLUX": [[1.0, 2.0], [3.0, 4.0]],
                    }
                ),
                encoding="utf-8",
            )
            png = plots_service.generate_heatmap(
                result_path, tmp / "flux.png", input_path
            )
            self.assertTrue(png.is_file())
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    @unittest.skipUnless(
        (ROOT / "solvers" / "runners").exists(), "solver directory missing"
    )
    def test_runner_executes_solver(self):
        try:
            get_solver_path("NTS_DD")
        except FileNotFoundError:
            self.skipTest("NTS_DD binary not found")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            config_path = tmp / "config.json"
            config_path.write_text(json.dumps(small_config()), encoding="utf-8")
            runner = SolverRunner(tmp / "inputs", tmp / "results")
            events: list[str] = []
            outcomes = runner.run([config_path], "NTS_DD", 1, events.append)

            self.assertEqual(len(outcomes), 1)
            outcome = outcomes[0]
            self.assertTrue(outcome.ok, outcome.error)
            self.assertEqual(outcome.status, 0)
            self.assertGreater(outcome.iterations, 0)
            self.assertIsNotNone(outcome.cpu)
            self.assertGreaterEqual(float(outcome.cpu), 0.0)
            self.assertTrue(outcome.input.is_file())
            self.assertTrue(outcome.output.is_file())
            data = json.loads(outcome.output.read_text(encoding="utf-8"))
            self.assertEqual(data["STATUS"], 0)
            self.assertEqual(len(data["MFLUX"]), 5)
            self.assertTrue(any("STATUS=0" in line for line in events))

    def test_runner_reports_invalid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad = small_config()
            bad["BC"] = [-0.5, 0.0, 0.0, 0.0]
            config_path = tmp / "bad.json"
            config_path.write_text(json.dumps(bad), encoding="utf-8")
            runner = SolverRunner(tmp / "inputs", tmp / "results")
            outcomes = runner.run([config_path], "NTS_DD", 1)
            self.assertEqual(len(outcomes), 1)
            self.assertFalse(outcomes[0].ok)
            self.assertTrue(outcomes[0].error)

    def test_config_store_round_trip(self):
        from tui2d.services import config_store

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config_2d_001.json"
            config_store.save_config(path, small_config(), "NTS_DD")
            loaded = config_store.load_config(path)
            self.assertEqual(loaded["_solver"], "NTS_DD")
            errors, message = config_store.validate(loaded)
            self.assertEqual(errors, [])
            self.assertIn("valid", message.lower())


class TestEntryPoint(unittest.TestCase):
    def test_app_does_not_import_heavy_modules(self):
        code = (
            "import sys; import tui2d.app; "
            "print(','.join(m for m in "
            "('matplotlib', 'pandas', 'openpyxl') if m in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "")

    def test_nts_tui_dim_2_fast_path(self):
        code = (
            "import sys; sys.argv = ['nts', 'tui', '--dim', '2']; "
            "import cli.main, tui2d.app; "
            "tui2d.app.main = lambda: 0; "
            "print(cli.main.main(), 'cli.commands' in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "0 False")


if __name__ == "__main__":
    unittest.main()
