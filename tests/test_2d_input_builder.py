"""Tests for the 2D input.txt builder (golden format of the C solvers)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.config import SimulationConfig
from core.input_builder import InputBuilder, _format_number


def sample_config(**overrides):
    config = {
        "N": 4,
        "NZ": 1,
        "zones": [{"sigma_t": 0.5, "sigma_s": 0.3}],
        "NR_X": 1,
        "XDOM": [{"length": 10.0, "nodes": 5}],
        "NR_Y": 1,
        "YDOM": [{"length": 10.0, "nodes": 5}],
        "ZMAP": [[1]],
        "QMAP": [[1.0]],
        "BC": [-1.0, 0.0, 2.0, 0.0],
        "TOL": 1e-5,
    }
    config.update(overrides)
    return SimulationConfig(**config)


GOLDEN_11 = "\n".join(
    [
        "4",
        "1",
        "0.5 0.3",
        "1",
        "10.0 5",
        "1",
        "10.0 5",
        "1",
        "1.0",
        "-1.0 0.0 2.0 0.0",
        "1e-05",
    ]
)


class TestFormatNumber(unittest.TestCase):
    def test_integers(self):
        self.assertEqual(_format_number(5), "5")
        self.assertEqual(_format_number(0), "0")

    def test_whole_floats(self):
        self.assertEqual(_format_number(10.0), "10.0")
        self.assertEqual(_format_number(-1), "-1")
        self.assertEqual(_format_number(-1.0), "-1.0")

    def test_fractions_and_exponents(self):
        self.assertEqual(_format_number(0.5), "0.5")
        self.assertEqual(_format_number(1e-5), "1e-05")


class TestGoldenInput(unittest.TestCase):
    def test_eleven_lines(self):
        builder = InputBuilder(sample_config())
        content = builder.build()
        self.assertEqual(content, GOLDEN_11)
        self.assertEqual(len(content.split("\n")), 11)

    def test_line_count_formula(self):
        config = sample_config(
            NZ=2,
            zones=[
                {"sigma_t": 0.5, "sigma_s": 0.3},
                {"sigma_t": 1.0, "sigma_s": 0.7},
            ],
            NR_X=2,
            XDOM=[
                {"length": 5.0, "nodes": 3},
                {"length": 5.0, "nodes": 4},
            ],
            NR_Y=2,
            YDOM=[
                {"length": 5.0, "nodes": 3},
                {"length": 5.0, "nodes": 4},
            ],
            ZMAP=[[1, 2], [2, 1]],
            QMAP=[[1.0, 0.5], [0.5, 1.0]],
        )
        lines = InputBuilder(config).build().split("\n")
        expected = 6 + config.NZ + config.NR_X + 3 * config.NR_Y
        self.assertEqual(len(lines), expected)

    def test_bc_order_is_canonical(self):
        builder = InputBuilder(sample_config(BC=[-1.0, 1.5, 0.0, 4.0]))
        lines = builder.build().split("\n")
        self.assertEqual(lines[-2], "-1.0 1.5 0.0 4.0")

    def test_incoming_flux_not_converted(self):
        builder = InputBuilder(sample_config(BC=[1.0, 1.0, 1.0, 1.0]))
        self.assertEqual(builder.build().split("\n")[-2], "1.0 1.0 1.0 1.0")

    def test_layout_sections(self):
        lines = InputBuilder(sample_config()).build().split("\n")
        self.assertEqual(lines[0], "4")       # N
        self.assertEqual(lines[1], "1")       # NZ
        self.assertEqual(lines[2], "0.5 0.3")  # zone
        self.assertEqual(lines[3], "1")       # NR_X
        self.assertEqual(lines[4], "10.0 5")  # XDOM
        self.assertEqual(lines[5], "1")       # NR_Y
        self.assertEqual(lines[6], "10.0 5")  # YDOM
        self.assertEqual(lines[7], "1")       # ZMAP
        self.assertEqual(lines[8], "1.0")     # QMAP
        self.assertEqual(lines[9], "-1.0 0.0 2.0 0.0")  # BC
        self.assertEqual(lines[10], "1e-05")  # TOL

    def test_save_writes_utf8_with_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "input.txt"
            InputBuilder(sample_config()).save(str(path))
            text = path.read_text(encoding="utf-8")
        self.assertEqual(text, GOLDEN_11 + "\n")

    def test_preview_short_content(self):
        preview = InputBuilder(sample_config()).preview()
        self.assertEqual(preview, GOLDEN_11)

    def test_preview_truncation(self):
        config = sample_config(
            NZ=2,
            zones=[
                {"sigma_t": 0.5, "sigma_s": 0.3},
                {"sigma_t": 1.0, "sigma_s": 0.7},
            ],
            NR_X=3,
            XDOM=[
                {"length": 5.0, "nodes": 3},
                {"length": 5.0, "nodes": 4},
                {"length": 5.0, "nodes": 5},
            ],
            NR_Y=3,
            YDOM=[
                {"length": 5.0, "nodes": 3},
                {"length": 5.0, "nodes": 4},
                {"length": 5.0, "nodes": 5},
            ],
            ZMAP=[[1, 2, 1], [2, 1, 2], [1, 2, 1]],
            QMAP=[[1.0, 0.5, 1.0], [0.5, 1.0, 0.5], [1.0, 0.5, 1.0]],
        )
        preview = InputBuilder(config).preview(max_lines=5)
        self.assertIn("more lines)", preview)
        self.assertLess(len(preview.split("\n")), 20)


if __name__ == "__main__":
    unittest.main()
