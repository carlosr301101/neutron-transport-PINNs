"""Literal DD equations (28)-(32) vs NTS_DD_1D (equivalence test).

The reference below uses the equations exactly as written in the DD
pseudoalgorithm:

  (28) psi_{m,i+1/2} = 2 psi_{m,i} - psi_{m,i-1/2}
  (29) psi_{m,i} = [2 psi_{m,i-1/2} + alpha (S_sc + S_f + S_m/sigma_t)]
                   / (2 + alpha)
  (30) S_sc = C_0 phi,  S_f = C_f phi
  (31) psi_{m,i-1/2} = 2 psi_{m,i} - psi_{m,i+1/2}
  (32) psi_{m,i} = [2 psi_{m,i+1/2} - alpha (S_sc + S_f + S_m/sigma_t)]
                   / (2 - alpha)

with alpha = sigma_t dx / mu (signed; negative for the leftgoing ordinate).
The test problem has no external or fission source, so S_f = S_m = 0.
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


def literal_dd(cells: int) -> tuple:
    """DD equations (28)-(32) for S2, written in the alpha form."""
    mu = np.array([1.0 / np.sqrt(3.0), -1.0 / np.sqrt(3.0)])
    omega = np.array([1.0, 1.0])
    dx = LENGTH / cells
    alpha = SIGMA_T * dx / mu          # signed: + for m=1, - for m=2
    c0 = SIGMA_S / SIGMA_T

    phi = np.zeros(cells)
    phi_old = np.zeros(cells)
    S_sc = np.zeros(cells)
    S_f = np.zeros(cells)              # no fission in this problem
    S_m = np.zeros(cells)              # no external source
    iteration = 0

    for iteration in range(1, 2001):
        # 3. Rightgoing sweep: eq. (29) then eq. (28)
        psi_in = 1.0                   # left BC: psi_{1,1/2} = 1
        psi_avg_pos = np.zeros(cells)
        psi_out_pos = np.zeros(cells)
        sum1 = np.zeros(cells)
        for i in range(cells):
            source = S_sc[i] + S_f[i] + S_m[i] / SIGMA_T
            psi = (2.0 * psi_in + alpha[0] * source) / (2.0 + alpha[0])
            psi_out = 2.0 * psi - psi_in
            psi_avg_pos[i] = psi
            psi_out_pos[i] = psi_out
            sum1[i] += psi * omega[0]
            psi_in = psi_out
        phi = 0.5 * sum1

        # 4. Leftgoing sweep: eq. (32) then eq. (31)
        psi_in = 0.0                   # right BC: psi_{2,I+1/2} = 0
        psi_avg_neg = np.zeros(cells)
        psi_out_neg = np.zeros(cells)
        sum2 = np.zeros(cells)
        for i in range(cells - 1, -1, -1):
            source = S_sc[i] + S_f[i] + S_m[i] / SIGMA_T
            psi = (2.0 * psi_in - alpha[1] * source) / (2.0 - alpha[1])
            psi_out = 2.0 * psi - psi_in
            psi_avg_neg[i] = psi
            psi_out_neg[i] = psi_out
            sum2[i] += psi * omega[1]
            psi_in = psi_out
        phi += 0.5 * sum2

        # 5. Convergence: max |1 - phi_new/phi_old| (zero-flux fallback)
        denom = np.where(np.abs(phi_old) > 1e-13, np.abs(phi_old), 1.0)
        error = np.max(np.abs(phi - phi_old) / denom)
        if error < EPSILON:
            break
        phi_old = phi.copy()
        S_sc = c0 * phi                # eq. (30)

    return (
        iteration,
        phi,
        psi_avg_pos,
        psi_avg_neg,
        psi_out_pos,
        psi_out_neg,
    )


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


class TestLiteralDDFormulas(unittest.TestCase):
    def _check(self, cells: int) -> None:
        (
            iteration,
            phi,
            avg_pos,
            avg_neg,
            out_pos,
            out_neg,
        ) = literal_dd(cells)
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
