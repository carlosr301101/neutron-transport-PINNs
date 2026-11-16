"""Boundary scalar/vector normalization tests."""

from __future__ import annotations

import contextlib
import io
import unittest

import numpy as np

from solvers.runners.NTS_DD_1D import Config


def base_config(**overrides):
    config = {
        "num_regions": 1,
        "num_zones": 1,
        "NC": [10],
        "HR": [10.0],
        "IZL": [1],
        "SCT": [1.0],
        "SCS": [0.9],
        "Q": [0.0],
        "N": 8,
        "NU_SIGF": [0.0],
        "MODE": "fixed_source",
    }
    config.update(overrides)
    return config


def make_config(**overrides):
    with contextlib.redirect_stdout(io.StringIO()):
        return Config(manual=False, **base_config(**overrides))


class TestBoundaryVector(unittest.TestCase):
    def test_scalar_expands_to_n_half(self):
        config = make_config(bound_left=0, bound_right=1)
        np.testing.assert_array_equal(config.bound_left, [0.0, 0.0, 0.0, 0.0])
        np.testing.assert_array_equal(config.bound_right, [1.0, 1.0, 1.0, 1.0])

    def test_single_element_list_expands(self):
        config = make_config(bound_left=[0], bound_right=[1])
        np.testing.assert_array_equal(config.bound_left, [0.0, 0.0, 0.0, 0.0])
        np.testing.assert_array_equal(config.bound_right, [1.0, 1.0, 1.0, 1.0])

    def test_full_vector_is_kept(self):
        config = make_config(
            bound_left=[0, 1, 1, 0],
            bound_right=[1, 0, 0, 1],
        )
        np.testing.assert_array_equal(config.bound_left, [0.0, 1.0, 1.0, 0.0])
        np.testing.assert_array_equal(config.bound_right, [1.0, 0.0, 0.0, 1.0])

    def test_invalid_length_has_clear_error(self):
        with self.assertRaisesRegex(
            ValueError, "bound_left must have 4 elements or one scalar"
        ):
            make_config(bound_left=[0, 1], bound_right=0)

    def test_reflective_scalar_is_safe(self):
        config = make_config(
            reflex_izq=True,
            bound_left=0,
            bound_right=1,
        )
        np.testing.assert_array_equal(config.bound_left, [0.0, 0.0, 0.0, 0.0])
        np.testing.assert_array_equal(config.bound_right, [1.0, 1.0, 1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
