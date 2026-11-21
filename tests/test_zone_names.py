"""Tests for the optional ZONE_NAMES presentation metadata."""

from __future__ import annotations

import unittest

from core.placeholders import (
    contains_placeholders,
    detect_placeholders,
    replace_placeholders,
)
from solvers.runners.NTS_DD_1D import Config

BASE = {
    "num_regions": 2,
    "num_zones": 2,
    "NC": [2, 2],
    "HR": [2.0, 2.0],
    "IZL": [1, 2],
    "SCT": [1.0, 0.5],
    "SCS": [0.9, 0.1],
    "NU_SIGF": [0.0, 0.0],
    "Q": [1.0, 0.0],
    "N": 2,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0.0],
    "bound_right": [0.0],
    "MODE": "fixed_source",
}


class TestZoneNamesConfig(unittest.TestCase):
    def test_zone_names_are_kept_in_as_dict(self):
        conf = Config(
            manual=False,
            ZONE_NAMES=["Reflector", "Core"],
            **BASE,
        )
        self.assertEqual(conf.ZONE_NAMES, ["Reflector", "Core"])
        self.assertEqual(conf.as_dict()["ZONE_NAMES"], ["Reflector", "Core"])

    def test_zone_names_are_optional(self):
        conf = Config(manual=False, **BASE)
        self.assertIsNone(conf.ZONE_NAMES)
        self.assertNotIn("ZONE_NAMES", conf.as_dict())

    def test_zone_names_round_trip(self):
        conf = Config(
            manual=False,
            ZONE_NAMES=["Reflector", "Core"],
            **BASE,
        )
        restored = Config(manual=False, **conf.as_dict())
        self.assertEqual(restored.ZONE_NAMES, ["Reflector", "Core"])

    def test_wrong_length_is_rejected(self):
        with self.assertRaises(ValueError):
            Config(manual=False, ZONE_NAMES=["Reflector"], **BASE)

    def test_empty_name_is_rejected(self):
        with self.assertRaises(ValueError):
            Config(manual=False, ZONE_NAMES=["Reflector", "  "], **BASE)

    def test_plain_string_is_rejected(self):
        with self.assertRaises(ValueError):
            Config(manual=False, ZONE_NAMES="Reflector, Core", **BASE)

    def test_zone_names_are_not_placeholders(self):
        cfg = {**BASE, "ZONE_NAMES": ["Reflector", "Core"]}
        self.assertEqual(detect_placeholders(cfg), set())
        self.assertFalse(contains_placeholders(cfg, {"Reflector", "Core"}))
        replaced = replace_placeholders(cfg, {"Reflector": 1.0, "Core": 2.0})
        self.assertEqual(replaced["ZONE_NAMES"], ["Reflector", "Core"])


if __name__ == "__main__":
    unittest.main()
