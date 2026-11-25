"""Tests for the 2D simulation configuration model."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from core.config import (
    BC_LABELS,
    SimulationConfig,
    describe_bc,
    is_valid_bc,
)


def base_config(**overrides):
    """Return a minimal valid 2D configuration."""
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
        "BC": [0.0, 0.0, 0.0, 0.0],
        "TOL": 1e-5,
    }
    config.update(overrides)
    return config


class TestBoundaryConditions(unittest.TestCase):
    def test_labels_follow_c_order(self):
        self.assertEqual(BC_LABELS, ("Left", "Bottom", "Right", "Top"))

    def test_valid_values(self):
        self.assertTrue(is_valid_bc(-1.0))
        self.assertTrue(is_valid_bc(0.0))
        self.assertTrue(is_valid_bc(1.0))
        self.assertTrue(is_valid_bc(2.5))

    def test_invalid_values(self):
        self.assertFalse(is_valid_bc(-0.5))
        self.assertFalse(is_valid_bc(-2.0))
        self.assertFalse(is_valid_bc(-1.5))

    def test_describe(self):
        self.assertEqual(describe_bc(-1.0), "Reflective")
        self.assertEqual(describe_bc(0.0), "Vacuum")
        self.assertEqual(describe_bc(1.0), "Incoming")
        self.assertEqual(describe_bc(3.5), "Incoming")

    def test_config_accepts_canonical_values(self):
        config = SimulationConfig(**base_config(BC=[-1.0, 0.0, 2.0, 0.5]))
        self.assertEqual(config.BC, [-1.0, 0.0, 2.0, 0.5])

    def test_config_preserves_order(self):
        config = SimulationConfig(**base_config(BC=[-1.0, 2.0, 0.0, 3.0]))
        self.assertEqual(config.BC[0], -1.0)  # left
        self.assertEqual(config.BC[1], 2.0)   # bottom
        self.assertEqual(config.BC[2], 0.0)   # right
        self.assertEqual(config.BC[3], 3.0)   # top

    def test_config_rejects_invalid_negative(self):
        for bad in (-0.5, -1.5, -2.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    SimulationConfig(**base_config(BC=[bad, 0.0, 0.0, 0.0]))

    def test_config_requires_four_values(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(BC=[0.0, 0.0, 0.0]))
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(BC=[0.0, 0.0, 0.0, 0.0, 0.0]))


class TestQuadratureOrder(unittest.TestCase):
    def test_even_values_in_range(self):
        for n in (2, 4, 6, 8, 10, 12, 14, 16, 18):
            with self.subTest(n=n):
                self.assertEqual(SimulationConfig(**base_config(N=n)).N, n)

    def test_odd_rejected(self):
        for n in (3, 5, 17):
            with self.subTest(n=n):
                with self.assertRaises(ValidationError):
                    SimulationConfig(**base_config(N=n))

    def test_out_of_range_rejected(self):
        for n in (0, 1, 20):
            with self.subTest(n=n):
                with self.assertRaises(ValidationError):
                    SimulationConfig(**base_config(N=n))


class TestSpatialRegions(unittest.TestCase):
    def test_minimum_nodes(self):
        self.assertEqual(
            SimulationConfig(**base_config(XDOM=[{"length": 10.0, "nodes": 3}])).XDOM[0].nodes,
            3,
        )

    def test_fewer_than_three_nodes_rejected(self):
        for nodes in (1, 2, 0, -1):
            with self.subTest(nodes=nodes):
                with self.assertRaises(ValidationError):
                    SimulationConfig(
                        **base_config(XDOM=[{"length": 10.0, "nodes": nodes}])
                    )

    def test_non_positive_length_rejected(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(YDOM=[{"length": 0.0, "nodes": 5}]))

    def test_totals_and_cell_centers(self):
        config = SimulationConfig(
            **base_config(
                NR_X=2,
                XDOM=[
                    {"length": 4.0, "nodes": 4},
                    {"length": 6.0, "nodes": 3},
                ],
                NR_Y=2,
                YDOM=[
                    {"length": 5.0, "nodes": 5},
                    {"length": 5.0, "nodes": 5},
                ],
                ZMAP=[[1, 1], [1, 1]],
                QMAP=[[1.0, 1.0], [1.0, 1.0]],
            )
        )
        self.assertEqual(config.total_nodes_x, 7)
        self.assertEqual(config.total_nodes_y, 10)
        self.assertAlmostEqual(config.total_length_x, 10.0)
        self.assertAlmostEqual(config.total_length_y, 10.0)

        centers_x = config.cell_centers_x()
        self.assertEqual(len(centers_x), 7)
        self.assertAlmostEqual(centers_x[0], 0.5)
        self.assertAlmostEqual(centers_x[3], 3.5)
        self.assertAlmostEqual(centers_x[4], 5.0)
        self.assertAlmostEqual(centers_x[-1], 9.0)


class TestMaps(unittest.TestCase):
    def test_zmap_dimensions(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(ZMAP=[[1], [1]]))

        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(ZMAP=[[1, 1]]))

    def test_zmap_values(self):
        config = SimulationConfig(
            **base_config(
                NZ=2,
                zones=[
                    {"sigma_t": 0.5, "sigma_s": 0.3},
                    {"sigma_t": 1.0, "sigma_s": 0.7},
                ],
                NR_X=2,
                XDOM=[
                    {"length": 5.0, "nodes": 5},
                    {"length": 5.0, "nodes": 5},
                ],
                NR_Y=2,
                YDOM=[
                    {"length": 5.0, "nodes": 5},
                    {"length": 5.0, "nodes": 5},
                ],
                ZMAP=[[1, 2], [2, 1]],
                QMAP=[[1.0, 0.5], [0.5, 1.0]],
            )
        )
        self.assertEqual(config.ZMAP, [[1, 2], [2, 1]])

    def test_zmap_out_of_range(self):
        for value in (0, 2, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    SimulationConfig(**base_config(ZMAP=[[value]]))

    def test_qmap_negative_rejected(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(QMAP=[[-0.1]]))

    def test_qmap_dimensions(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(QMAP=[[1.0], [1.0]]))

    def test_zero_source_allowed(self):
        self.assertEqual(SimulationConfig(**base_config(QMAP=[[0.0]])).QMAP, [[0.0]])


class TestZones(unittest.TestCase):
    def test_sigma_s_must_be_lower_than_sigma_t(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(
                **base_config(zones=[{"sigma_t": 0.5, "sigma_s": 0.5}])
            )

    def test_zone_count_must_match_nz(self):
        with self.assertRaises(ValidationError):
            SimulationConfig(**base_config(NZ=2))


class TestJsonRoundTrip(unittest.TestCase):
    def test_round_trip_utf8(self):
        config = SimulationConfig(**base_config())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config.to_json_file(str(path))
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertIn('"BC"', text)
            again = SimulationConfig.from_json_file(str(path))
        self.assertEqual(again.model_dump(), config.model_dump())

    def test_comments_are_ignored(self):
        data = base_config()
        data["_comment"] = "ignore me"
        data["_BC_hint"] = "left bottom right top"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            config = SimulationConfig.from_json_file(str(path))
        self.assertNotIn("_comment", config.model_dump())


if __name__ == "__main__":
    unittest.main()
