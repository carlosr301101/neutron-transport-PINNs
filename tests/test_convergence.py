"""Tests for the scalar-flux convergence criterion."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from solvers.runners.NTS_DD_1D import Runner


def make_runner(new_flux, epsilon: float = 1e-5) -> Runner:
    runner = Runner.__new__(Runner)
    runner.scalar_flux = np.asarray(new_flux, dtype=float)
    runner.config = SimpleNamespace(epsilon=epsilon)
    runner.iteration = 0
    return runner


class TestRelativeFluxChange(unittest.TestCase):
    def test_uses_old_flux_as_denominator(self):
        # |1 - 2/1| = 1.0 (the new-flux denominator would give 0.5)
        self.assertAlmostEqual(
            Runner._relative_flux_change([1.0, 1.0], [2.0, 2.0]), 1.0
        )

    def test_matches_one_minus_ratio(self):
        old = [1.0, 2.0]
        new = [1.0 + 9e-6, 2.0 + 1.8e-5]
        self.assertAlmostEqual(
            Runner._relative_flux_change(old, new), 9e-6, delta=1e-12
        )

    def test_negative_flux(self):
        self.assertAlmostEqual(
            Runner._relative_flux_change([-1.0], [-1.0 - 1e-5]),
            1e-5,
            delta=1e-12,
        )

    def test_zero_old_flux_falls_back_to_absolute(self):
        self.assertAlmostEqual(
            Runner._relative_flux_change([0.0, 1.0], [1e-6, 1.0]), 1e-6
        )
        self.assertEqual(
            Runner._relative_flux_change([0.0, 1.0], [0.0, 1.0]), 0.0
        )

    def test_check_increments_iteration(self):
        runner = make_runner([1.0])
        self.assertEqual(runner.iteration, 0)
        runner.check_convergence([1.0], verbose=False)
        self.assertEqual(runner.iteration, 1)

    def test_below_and_above_threshold(self):
        self.assertTrue(
            make_runner([1.0 + 9e-6]).check_convergence([1.0], verbose=False)
        )
        self.assertFalse(
            make_runner([1.0 + 2e-5]).check_convergence([1.0], verbose=False)
        )

    def test_custom_tolerance(self):
        runner = make_runner([1.0 + 2e-5], epsilon=1e-5)
        self.assertTrue(
            runner.check_convergence([1.0], verbose=False, tol=1e-4)
        )


if __name__ == "__main__":
    unittest.main()
