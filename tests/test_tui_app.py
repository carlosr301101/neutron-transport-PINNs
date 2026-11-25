"""Smoke tests for the Textual application."""

from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Button, Input, Select, Static, TabbedContent

from tui.app import NTSApp
from tui.screens.config_editor import ConfigEditorPane
from tui.screens.placeholders import PlaceholdersPane
from tui.screens.plot_studio import PlotStudioPane
from tui.screens.results import ResultsPane
from tui.screens.run_manager import RunManagerPane
from tui.schema import DEFAULT_CONFIG
from tui.widgets import RegionTable, ZoneTable
from tui.widgets.image_preview import ImagePreview


class TestTUIApp(unittest.IsolatedAsyncioTestCase):
    async def test_mount_and_tabs(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            self.assertEqual(tabs.active, "tab-dashboard")
            for tab in (
                "tab-config",
                "tab-run",
                "tab-results",
                "tab-plots",
                "tab-placeholders",
                "tab-export",
            ):
                tabs.active = tab
                await pilot.pause()
                self.assertEqual(tabs.active, tab)

    async def test_config_editor_validates_and_saves(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            pane._validate()
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn(
                "valid", pane.query_one("#cfg-status", Static).content.lower()
            )

            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "config.json"
                pane.query_one("#cfg-path", Input).value = str(path)
                pane._save()
                self.assertTrue(path.exists())
                self.assertIn(
                    "saved", pane.query_one("#cfg-status", Static).content.lower()
                )

    async def test_default_cells_is_ten(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            self.assertEqual(
                pane.query_one("#region-0-cells", Input).value, "10"
            )

    async def test_zone_names_save_and_load(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            pane.query_one(RegionTable).set_values(
                [2, 2], [2.0, 2.0], [1, 2], [1.0, 0.0]
            )
            pane.query_one(ZoneTable).set_values(
                [1.0, 0.5], [0.9, 0.1], ["Reflector", "Core"]
            )
            await pilot.pause()

            config = pane._collect()
            self.assertEqual(config["ZONE_NAMES"], ["Reflector", "Core"])

            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "config.json"
                pane.query_one("#cfg-path", Input).value = str(path)
                pane._save()
                self.assertTrue(path.exists())
                saved = json.loads(path.read_text())
            self.assertEqual(saved["ZONE_NAMES"], ["Reflector", "Core"])

            pane._populate(saved)
            await pilot.pause()
            self.assertEqual(
                pane.query_one("#zone-0-name", Input).value, "Reflector"
            )
            self.assertEqual(
                pane.query_one("#zone-1-name", Input).value, "Core"
            )

    async def test_partial_zone_names_fail_to_save(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            pane.query_one(RegionTable).set_values(
                [2, 2], [2.0, 2.0], [1, 2], [1.0, 0.0]
            )
            pane.query_one(ZoneTable).set_values(
                [1.0, 0.5], [0.9, 0.1], ["Reflector"]
            )
            await pilot.pause()
            with self.assertRaises(ValueError):
                pane._collect()

    async def test_validate_does_not_block_the_ui(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            await app.workers.wait_for_complete()
            await pilot.pause()

            def slow_validate(config):
                time.sleep(1.5)
                return [], "Configuration is valid."

            with patch(
                "tui.screens.config_editor.validate_config",
                side_effect=slow_validate,
            ):
                started = time.perf_counter()
                pane._validate()
                await pilot.pause()
                elapsed = time.perf_counter() - started
                self.assertLess(elapsed, 0.75)
                self.assertIn(
                    "Validating",
                    str(pane.query_one("#cfg-status", Static).content),
                )
                self.assertTrue(
                    pane.query_one("#cfg-validate", Button).disabled
                )
                await app.workers.wait_for_complete()
                await pilot.pause()

            status = str(pane.query_one("#cfg-status", Static).content).lower()
            self.assertIn("valid", status)
            self.assertFalse(
                pane.query_one("#cfg-validate", Button).disabled
            )

    async def test_boundary_scalar_and_vector(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            pane.query_one("#cfg-N", Input).value = "8"
            pane.query_one("#cfg-bound_left", Input).value = "0"
            pane.query_one("#cfg-bound_right", Input).value = "1"
            config = pane._collect()
            self.assertEqual(config["bound_left"], [0.0] * 4)
            self.assertEqual(config["bound_right"], [1.0] * 4)

            pane.query_one("#cfg-bound_left", Input).value = "0,1,1,0"
            self.assertEqual(pane._collect()["bound_left"], [0.0, 1.0, 1.0, 0.0])

            pane.query_one("#cfg-bound_left", Input).value = "0,1"
            with self.assertRaises(ValueError):
                pane._collect()

    async def test_reflection_hides_incoming_flux(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            await pilot.pause()
            pane._widgets["reflex_izq"].value = True
            pane._widgets["reflex_der"].value = True
            await pilot.pause()
            self.assertFalse(pane._rows["bound_left"].display)
            self.assertFalse(pane._rows["bound_right"].display)
            config = pane._collect()
            self.assertEqual(config["bound_left"], [0.0])
            self.assertEqual(config["bound_right"], [0.0])

    async def test_config_preloads_once(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            for _ in range(20):
                if app.query(ConfigEditorPane):
                    break
                await pilot.pause(0.05)
            panes = app.query(ConfigEditorPane)
            self.assertEqual(len(panes), 1)
            pane = panes.first()
            again = await app._ensure_pane("tab-config")
            self.assertIs(pane, again)

    async def test_results_and_plots_load_on_activation(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            self.assertEqual(len(app.query(ResultsPane)), 0)
            self.assertEqual(len(app.query(PlotStudioPane)), 0)

            tabs = app.query_one("#tabs", TabbedContent)
            tabs.active = "tab-results"
            await pilot.pause()
            results = app.query_one(ResultsPane)
            self.assertTrue(results._loaded)

            tabs.active = "tab-plots"
            await pilot.pause()
            plots = app.query_one(PlotStudioPane)
            self.assertTrue(plots._loaded)

    async def test_region_and_zone_tables_are_visible(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            self.assertGreater(app.query_one("#region-table").size.height, 5)
            self.assertGreater(app.query_one("#zone-table").size.height, 4)
            self.assertTrue(app.query_one("#region-add").display)
            self.assertTrue(app.query_one("#zone-add").display)

    async def test_blank_mode_round_trip(self):
        import copy

        from tui.schema import DEFAULT_CONFIG

        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            config = copy.deepcopy(DEFAULT_CONFIG)
            config["MODE"] = None
            pane._populate(config)
            self.assertEqual(pane._collect()["MODE"], "fixed_source")

    async def test_mode_visibility_and_sanitization(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            mode = pane._widgets["MODE"]

            mode.value = "eigenvalue"
            await pilot.pause()
            self.assertTrue(pane.query_one("#fission-wrap").display)
            self.assertFalse(pane._rows["K_EFF"].display)
            self.assertTrue(pane._rows["K0"].display)
            self.assertFalse(pane.query_one("#region-q-head").display)

            mode.value = "fixed_k"
            await pilot.pause()
            self.assertTrue(pane._rows["K_EFF"].display)
            self.assertFalse(pane._rows["K0"].display)

            mode.value = "fixed_source"
            await pilot.pause()
            self.assertFalse(pane.query_one("#fission-wrap").display)
            config = pane._collect()
            self.assertEqual(config["NU_SIGF"], [0.0])
            self.assertIsNone(config["SIGMA_F"])
            self.assertIsNone(config["POWER_KW"])

    async def test_region_zone_tables_round_trip(self):
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            await pilot.pause(0.1)
            pane = app.query_one(ConfigEditorPane)
            await pilot.pause(0.1)
            config = {
                "num_regions": 5,
                "num_zones": 3,
                "NC": [10, 20, 40, 20, 10],
                "HR": [10.0, 20.0, 40.0, 20.0, 10.0],
                "IZL": [1, 2, 3, 2, 1],
                "SCT": [1.0, 1.0, 1.0],
                "SCS": [0.9, 0.5, 0.5],
                "Q": [0.0, 0.55, 0.48, 0.55, 0.0],
                "NU_SIGF": [0.0, 0.55, 0.48],
                "SIGMA_F": None,
                "MODE": "eigenvalue",
            }
            pane._populate(config)
            await pilot.pause(0.1)
            out = pane._collect()
            self.assertEqual(out["num_regions"], 5)
            self.assertEqual(out["num_zones"], 3)
            self.assertEqual(out["NC"], config["NC"])
            self.assertEqual(out["HR"], config["HR"])
            self.assertEqual(out["IZL"], config["IZL"])
            self.assertEqual(out["SCT"], config["SCT"])
            self.assertEqual(out["SCS"], config["SCS"])
            self.assertEqual(out["NU_SIGF"], config["NU_SIGF"])

    async def test_image_preview_fallback(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-plots"
            await pilot.pause()
            preview = app.query_one(ImagePreview)
            with patch(
                "tui.widgets.image_preview.detect_image_protocol",
                return_value=None,
            ):
                preview.show(Path(tempfile.gettempdir()) / "does-not-exist.png")
                await pilot.pause()
            self.assertIn(
                "not supported",
                preview.query_one("#preview-status", Static).content.lower(),
            )

    async def test_plot_studio_has_no_direction_selector(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-plots"
            await pilot.pause()
            self.assertEqual(len(app.query("#plot-directions")), 0)

    async def test_plot_source_selects_existing_result(self):
        app = NTSApp()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "output_1d_999.json"
            source.write_text(json.dumps({"runs": []}))
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.pause()
                app.query_one("#tabs", TabbedContent).active = "tab-plots"
                await pilot.pause()
                pane = app.query_one(PlotStudioPane)
                with patch("tui.screens.plot_studio.list_outputs", return_value=[]):
                    pane.set_source(source)
                    await pilot.pause()
                status = str(pane.query_one("#plot-status", Static).content)
                self.assertNotIn("not listed", status.lower())
                selected = pane.query_one("#plot-result", Select).value
                self.assertEqual(str(selected), str(source))

    async def test_angular_kind_selects_single_run(self):
        app = NTSApp()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "output_1d_999.json"
            source.write_text(
                json.dumps(
                    {"runs": [{"config_name": "run_a"}, {"config_name": "run_b"}]}
                )
            )
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.pause()
                app.query_one("#tabs", TabbedContent).active = "tab-plots"
                await pilot.pause()
                pane = app.query_one(PlotStudioPane)
                pane.query_one("#plot-result", Select).set_options(
                    [(source.name, str(source))]
                )
                pane.query_one("#plot-result", Select).value = str(source)
                await pilot.pause()
                pane.query_one("#plot-kind", Select).value = "angular"
                await pilot.pause()
                run_value = pane.query_one("#plot-run", Select).value
                self.assertNotEqual(str(run_value), "all")

    async def test_dashboard_has_no_latest_result(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            text = str(app.query_one("#dash-status", Static).render())
            self.assertNotIn("Latest result", text)
            self.assertIn("Result files", text)

    async def test_refresh_all_updates_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tui.services.results.RESULTS_DIR", Path(tmp)):
                app = NTSApp()
                async with app.run_test(size=(140, 50)) as pilot:
                    await pilot.pause()
                    (Path(tmp) / "output_1d_001.json").write_text(
                        json.dumps({"runs": []})
                    )
                    app.refresh_all()
                    await pilot.pause()
                    text = str(app.query_one("#dash-status", Static).render())
                    self.assertIn("Result files  1", text)

    async def test_run_and_placeholders_expose_cancel(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            tabs.active = "tab-run"
            await pilot.pause()
            self.assertTrue(app.query_one("#run-cancel", Button).disabled)
            tabs.active = "tab-placeholders"
            await pilot.pause()
            self.assertTrue(app.query_one("#ph-cancel", Button).disabled)

    async def test_unmount_cancels_a_running_solver(self):
        app = NTSApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-run"
            await pilot.pause()
            pane = app.query_one(RunManagerPane)
            fake = _FakeRun()
            pane._process = fake
            app.on_unmount()
            self.assertTrue(fake.cancelled)

    async def test_results_detail_maps_skipped_runs(self):
        payload = {
            "runs": [
                {"config_name": "alpha", "iteration": 1},
                "junk",
                {"config_name": "beta", "iteration": 7},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "output_1d_001.json").write_text(json.dumps(payload))
            with patch("tui.services.results.RESULTS_DIR", Path(tmp)):
                app = NTSApp()
                async with app.run_test(size=(140, 50)) as pilot:
                    await pilot.pause()
                    app.query_one("#tabs", TabbedContent).active = "tab-results"
                    await pilot.pause()
                    pane = app.query_one(ResultsPane)
                    pane.on_data_table_row_selected(_FakeRowSelected(1))
                    detail = str(pane.query_one("#results-detail", Static).render())
                    self.assertIn("beta", detail)


    async def test_use_in_plots_switches_tab_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "output_1d_001.json"
            source.write_text(
                json.dumps(
                    {"runs": [{"config_name": "run_a", "mode": "eigenvalue",
                               "scalar_flux": [1.0, 2.0, 3.0]}]}
                )
            )
            with (
                patch("tui.screens.results.list_outputs", return_value=[source]),
                patch("tui.screens.plot_studio.list_outputs", return_value=[source]),
            ):
                app = NTSApp()
                async with app.run_test(size=(140, 50)) as pilot:
                    await pilot.pause()
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "tab-results"
                    for _ in range(10):
                        await pilot.pause()
                        if app.query("#results-to-plots"):
                            break
                    await pilot.click("#results-to-plots")
                    for _ in range(8):
                        await pilot.pause()
                    self.assertEqual(tabs.active, "tab-plots")
                    pane = app.query_one(PlotStudioPane)
                    self.assertEqual(
                        str(pane.query_one("#plot-result", Select).value),
                        str(source),
                    )

    async def test_placeholders_range_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config_1d_001.json"
            config.write_text(json.dumps({"SCS": ["QQ"], "NC": [1]}))
            with patch(
                "tui.screens.placeholders.list_configs", return_value=[config]
            ):
                app = NTSApp()
                async with app.run_test(size=(140, 50)) as pilot:
                    await pilot.pause()
                    tabs = app.query_one("#tabs", TabbedContent)
                    tabs.active = "tab-placeholders"
                    for _ in range(3):
                        await pilot.pause()
                    pane = app.query_one(PlaceholdersPane)
                    select = pane.query_one("#ph-file", Select)
                    select.set_options([(config.name, str(config))])
                    select.value = str(config)
                    await pilot.pause()
                    pane._load()
                    await pilot.pause()
                    self.assertEqual(pane._placeholders, ["QQ"])

                    pane.query_one("#ph-range-QQ", Input).value = "10:20:1"
                    pane._preview()
                    await pilot.pause()
                    status = str(pane.query_one("#ph-status", Static).content)
                    self.assertIn("11 configuration(s)", status)

                    pane.query_one("#ph-range-QQ", Input).value = "20:10:1"
                    pane._preview()
                    await pilot.pause()
                    status = str(pane.query_one("#ph-status", Static).content)
                    self.assertIn("End must be", status)

    async def test_power_normalization_fields_are_conditional(self):
        power_fields = ("POWER_KW", "E_F_MEV", "NU", "AREA_CM2")
        app = NTSApp()
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause()
            app.query_one("#tabs", TabbedContent).active = "tab-config"
            for _ in range(3):
                await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
            switch = pane._widgets["power_normalization"]

            # fixed_source: todo oculto
            self.assertFalse(pane._rows["power_normalization"].display)
            for key in power_fields:
                self.assertFalse(pane._rows[key].display)

            # eigenvalue: switch visible, campos aún ocultos
            pane._widgets["MODE"].value = "eigenvalue"
            await pilot.pause()
            self.assertTrue(pane._rows["power_normalization"].display)
            for key in power_fields:
                self.assertFalse(pane._rows[key].display)

            # encendido: aparecen los cuatro campos
            switch.value = True
            await pilot.pause()
            for key in power_fields:
                self.assertTrue(pane._rows[key].display)

            # encendido sin POWER_KW -> error de formulario
            with self.assertRaises(ValueError):
                pane.collect_config()

            pane._widgets["POWER_KW"].value = "10"
            config = pane.collect_config()
            self.assertEqual(config["POWER_KW"], 10.0)
            self.assertNotIn("power_normalization", config)

            # apagado: se oculta y no se normaliza
            switch.value = False
            await pilot.pause()
            for key in power_fields:
                self.assertFalse(pane._rows[key].display)
            self.assertIsNone(pane.collect_config()["POWER_KW"])

            # cargar un config con POWER_KW enciende el switch
            config = copy.deepcopy(DEFAULT_CONFIG)
            config.update({"MODE": "eigenvalue", "POWER_KW": 5.0,
                           "NU_SIGF": [0.1]})
            pane._populate(config)
            await pilot.pause()
            self.assertTrue(switch.value)
            for key in power_fields:
                self.assertTrue(pane._rows[key].display)


class _FakeRun:
    """Stand-in for ``RunProcess`` that records cancellation."""

    is_running = True

    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self, timeout: float = 5.0) -> None:
        self.cancelled = True


class _FakeRowSelected:
    """Minimal ``DataTable.RowSelected`` replacement."""

    def __init__(self, cursor_row: int) -> None:
        self.cursor_row = cursor_row


if __name__ == "__main__":
    unittest.main()
