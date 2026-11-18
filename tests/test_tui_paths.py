"""Tests for the shared path helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tui.services.paths import numbered_path, resolve_path, unique_path


class TestNumberedPath(unittest.TestCase):
    def test_empty_directory_starts_at_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = numbered_path(Path(tmp), "output_1d_")
            self.assertEqual(path.name, "output_1d_001.json")

    def test_uses_highest_index_not_last_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in ("output_1d_999.json", "output_1d_1000.json"):
                (directory / name).write_text("{}")
            path = numbered_path(directory, "output_1d_")
            self.assertEqual(path.name, "output_1d_1001.json")
            self.assertFalse(path.exists())

    def test_never_returns_an_existing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "output_1d_003.json").write_text("{}")
            (directory / "output_1d_zzz.json").write_text("{}")
            path = numbered_path(directory, "output_1d_")
            self.assertEqual(path.name, "output_1d_004.json")
            self.assertFalse(path.exists())

    def test_custom_suffix_and_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = numbered_path(Path(tmp), "plot_", suffix=".png", width=2)
            self.assertEqual(path.name, "plot_01.png")


class TestUniquePath(unittest.TestCase):
    def test_free_path_is_returned_as_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scalar.png"
            self.assertEqual(unique_path(path), path)

    def test_taken_path_gets_a_numbered_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scalar.png"
            path.write_text("x")
            sibling = unique_path(path)
            self.assertEqual(sibling.name, "scalar_001.png")
            self.assertFalse(sibling.exists())


class TestResolvePath(unittest.TestCase):
    def test_relative_path_uses_the_base(self):
        base = Path(tempfile.gettempdir()) / "nts-base"
        self.assertEqual(
            resolve_path("outputs/results/a.json", base),
            base / "outputs/results/a.json",
        )

    def test_absolute_path_is_kept(self):
        absolute = Path(tempfile.gettempdir()) / "a.json"
        self.assertEqual(resolve_path(absolute, Path(tempfile.gettempdir())), absolute)


if __name__ == "__main__":
    unittest.main()
