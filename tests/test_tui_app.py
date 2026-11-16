"""Smoke tests for the Textual application."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Input, Static, TabbedContent

from tui.app import NTSApp
from tui.screens.config_editor import ConfigEditorPane
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
            self.assertIsNone(pane._collect()["MODE"])

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


if __name__ == "__main__":
    unittest.main()
