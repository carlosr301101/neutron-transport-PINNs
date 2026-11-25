"""Template path resolution for source checkouts and installed wheels."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import utils.paths as paths
from utils.paths import get_template_path


class TestTemplatePath(unittest.TestCase):
    def test_bundled_template_is_used_when_the_work_root_has_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(paths, "TEMPLATES_DIR", Path(tmp) / "templates"):
                path = get_template_path()
        self.assertEqual(path.name, "base_input.json")
        self.assertTrue(path.is_file())

    def test_user_template_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            templates = Path(tmp) / "templates"
            templates.mkdir()
            custom = templates / "base_input.json"
            custom.write_text('{"N": 2}', encoding="utf-8")
            with patch.object(paths, "TEMPLATES_DIR", templates):
                self.assertEqual(get_template_path(), custom)


if __name__ == "__main__":
    unittest.main()
