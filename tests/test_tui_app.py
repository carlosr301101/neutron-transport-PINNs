"""Smoke tests for the Textual application."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Input, Select, Static, TabbedContent

from tui.app import NTSApp
from tui.screens.config_editor import ConfigEditorPane
from tui.screens.plot_studio import PlotStudioPane
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
                "tab-sweep",
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
            await pilot.pause()
            pane = app.query_one(ConfigEditorPane)
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
            await pilot.pause()
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
                preview.show("/tmp/does-not-exist.png")
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


if __name__ == "__main__":
    unittest.main()
