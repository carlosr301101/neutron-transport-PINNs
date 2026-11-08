"""Equivalence test: NTS_DD_1D vs the literal DD pseudoalgorithm (S2).

The reference below implements the five steps of the DD pseudoalgorithm
(input, initialization, rightgoing sweep, leftgoing sweep, convergence)
exactly, for the 20 cm slab with Sigma_t = 1, Sigma_s = 0.97, S2, a unit
incoming flux on the left and vacuum on the right.
"""

from __future__ import annotations

import contextlib
import io
import unittest

import numpy as np

from solvers.runners.NTS_DD_1D import Config, Runner

LENGTH = 20.0
SIGMA_T = 1.0
SIGMA_S = 0.97
EPSILON = 1e-5


def temp_dd(cells: int) -> tuple:
    """Literal DD pseudoalgorithm for S2 (positive and negative ordinates)."""
    mu = 1.0 / np.sqrt(3.0)
    dx = LENGTH / cells
    a = mu / dx

    phi = np.zeros(cells)
    phi_old = np.zeros(cells)
    S_sc = np.zeros(cells)
    iteration = 0

    for iteration in range(1, 2001):
        # 3. Rightgoing sweep (m = 1)
        psi_in = 1.0
        avg_pos = np.zeros(cells)
        out_pos = np.zeros(cells)
        for i in range(cells):
            out = ((a - 0.5 * SIGMA_T) * psi_in + S_sc[i]) / (
                a + 0.5 * SIGMA_T
            )
            avg = 0.5 * (psi_in + out)
            out_pos[i] = out
            avg_pos[i] = avg
            phi[i] = 0.5 * avg
            psi_in = out

        # 4. Leftgoing sweep (m = 2)
        psi_in = 0.0
        avg_neg = np.zeros(cells)
        out_neg = np.zeros(cells)
        for i in range(cells - 1, -1, -1):
            out = ((a - 0.5 * SIGMA_T) * psi_in + S_sc[i]) / (
                a + 0.5 * SIGMA_T
            )
            avg = 0.5 * (psi_in + out)
            out_neg[i] = out
            avg_neg[i] = avg
            phi[i] += 0.5 * avg
            psi_in = out

        # 5. Convergence: max |1 - phi_new/phi_old| < epsilon
        denom = np.where(np.abs(phi_old) > 1e-13, np.abs(phi_old), 1.0)
        error = np.max(np.abs(phi - phi_old) / denom)
        if error < EPSILON:
            break
        phi_old = phi.copy()
        S_sc = SIGMA_S * phi

    return iteration, phi, avg_pos, avg_neg, out_pos, out_neg


def run_solver(cells: int) -> dict:
    config = {
        "num_regions": 1,
        "num_zones": 1,
        "NC": [cells],
        "HR": [LENGTH],
        "IZL": [1],
        "SCT": [SIGMA_T],
        "SCS": [SIGMA_S],
        "NU_SIGF": [0.0],
        "Q": [0.0],
        "N": 2,
        "SPATIAL_SCHEME": "DD",
        "MODE": "fixed_source",
        "reflex_izq": False,
        "reflex_der": False,
        "bound_left": [1.0],
        "bound_right": [0.0],
    }
    with contextlib.redirect_stdout(io.StringIO()):
        return Runner(Config(manual=False, **config))()


class TestDDPseudocodeEquivalence(unittest.TestCase):
    def _check(self, cells: int) -> None:
        (
            iteration,
            phi,
            avg_pos,
            avg_neg,
            out_pos,
            out_neg,
        ) = temp_dd(cells)
        result = run_solver(cells)

        self.assertEqual(iteration, result["iteration"])

        np.testing.assert_allclose(
            phi, np.asarray(result["scalar_flux"]), rtol=0.0, atol=1e-12
        )
        angular = np.asarray(result["angular_flux"])
        np.testing.assert_allclose(
            avg_pos, angular[:, 1], rtol=0.0, atol=1e-12
        )
        np.testing.assert_allclose(
            avg_neg, angular[:, 0], rtol=0.0, atol=1e-12
        )
        right = np.asarray(result["PSI_RIGHT"])[:, 0]
        left = np.asarray(result["PSI_LEFT"])[:, 0]
        np.testing.assert_allclose(
            out_pos, right[1:], rtol=0.0, atol=1e-12
        )
        np.testing.assert_allclose(
            out_neg, left[:-1], rtol=0.0, atol=1e-12
        )

    def test_five_cells(self):
        self._check(5)

    def test_ten_cells(self):
        self._check(10)


if __name__ == "__main__":
    unittest.main()
