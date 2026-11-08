"""Tests for the 1D multiplicative-media extension of NTS_DD_1D.

Run from the repository root:

    uv run python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import io
import unittest

import numpy as np

from solvers.runners.NTS_DD_1D import Config, Runner


def run_config(**overrides) -> dict:
    """Build and run a NTS_DD_1D configuration without printing to stdout."""
    cfg = {
        "num_regions": 1,
        "num_zones": 1,
        "NC": [100],
        "HR": [20.0],
        "IZL": [1],
        "SCT": [1.0],
        "SCS": [0.9],
        "NU_SIGF": [0.11],
        "Q": [0.0],
        "N": 8,
        "reflex_izq": False,
        "reflex_der": False,
        "bound_left": [0, 0, 0, 0],
        "bound_right": [0, 0, 0, 0],
        "MODE": "eigenvalue",
    }
    cfg.update(overrides)
    with contextlib.redirect_stdout(io.StringIO()):
        conf = Config(manual=False, **cfg)
        result = Runner(conf)()
    return result


class TestMultiplicativeMedia(unittest.TestCase):
    def test_reflective_infinite_medium(self):
        """Reflective slab has no leakage: k_eff = nu*Sigma_f / Sigma_a."""
        result = run_config(
            NC=[20],
            SCT=[1.0],
            SCS=[0.5],
            NU_SIGF=[0.3],
            reflex_izq=True,
            reflex_der=True,
        )
        self.assertTrue(result["k_converged"])
        self.assertAlmostEqual(result["k_eff"], 0.6, delta=1e-6)
        self.assertAlmostEqual(result["k_balance"], 0.6, delta=1e-6)

    def test_benchmark_20cm_vacuum(self):
        """20 cm homogeneous slab, vacuum, S8: k_eff ~= 1.02668."""
        result = run_config(NC=[100])
        self.assertTrue(result["k_converged"])
        self.assertAlmostEqual(result["k_eff"], 1.02668, delta=2e-4)
        self.assertAlmostEqual(
            result["k_eff"], result["k_balance"], delta=1e-4
        )

    def test_fixed_k_at_eigenvalue_is_stationary(self):
        """fixed_k at k* without source: balance k must reproduce k*."""
        critical = run_config(NC=[40])
        k_star = critical["k_eff"]
        result = run_config(NC=[40], MODE="fixed_k", K_EFF=k_star)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["k_balance"], k_star, delta=1e-3)

    def test_driven_subcritical_balance(self):
        """Driven reflective slab with k_inf = 0.5: balance k = 0.5."""
        result = run_config(
            NC=[20],
            SCS=[0.9],
            NU_SIGF=[0.05],
            Q=[1.0],
            MODE="driven",
            reflex_izq=True,
            reflex_der=True,
        )
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["k_eff"], 1.0, delta=1e-12)
        self.assertAlmostEqual(result["k_balance"], 0.5, delta=1e-4)

    def test_power_default_nu(self):
        """POWER_KW without NU uses 2.49 (U-238) to derive Sigma_f."""
        cfg = {
            "num_regions": 1, "num_zones": 1, "NC": [20], "HR": [20.0],
            "IZL": [1], "SCT": [1.0], "SCS": [0.9], "NU_SIGF": [0.11],
            "Q": [0.0], "N": 8, "reflex_izq": False, "reflex_der": False,
            "bound_left": [0] * 4, "bound_right": [0] * 4,
            "MODE": "eigenvalue", "POWER_KW": 10.0, "E_F_MEV": 200.0,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            conf = Config(manual=False, **cfg)
            result = Runner(conf)()
        self.assertEqual(conf.NU, 2.49)
        self.assertAlmostEqual(result["power_w"], 10_000.0, delta=1e-6)

    def test_sweep_counters(self):
        eigen = run_config(NC=[20])
        self.assertGreater(eigen["iteration"], 0)
        self.assertEqual(
            eigen["iteration_eigenvalue"], eigen["outer_iterations"]
        )
        fixed = run_config(
            NC=[20], MODE="fixed_source", NU_SIGF=[0.0], Q=[1.0]
        )
        self.assertGreater(fixed["iteration"], 0)
        self.assertIsNone(fixed["iteration_eigenvalue"])

    def test_power_normalization(self):
        """POWER_KW scales the flux so that the integrated power is 10 kW."""
        result = run_config(
            NC=[100],
            POWER_KW=10.0,
            E_F_MEV=200.0,
            NU=2.4,
            AREA_CM2=1.0,
        )
        self.assertAlmostEqual(result["power_w"], 10_000.0, delta=1e-6)
        sigma_f = 0.11 / 2.4
        dx = 20.0 / 100
        power_w = (
            2.0
            * 1.0
            * 200.0
            * 1.602176634e-13
            * float(np.sum(sigma_f * result["scalar_flux"] * dx))
        )
        self.assertAlmostEqual(power_w, 10_000.0, delta=1e-3)
        self.assertGreater(result["power_unnormalized"], 0.0)
        self.assertAlmostEqual(
            result["power_scale"] * result["power_unnormalized"],
            10_000.0,
            delta=1e-6,
        )

    def test_fixed_source_regression(self):
        """NU_SIGF=0 keeps the historical fixed-source behaviour."""
        result = run_config(
            NC=[20],
            NU_SIGF=[0.0],
            MODE="fixed_source",
            Q=[1.0],
            reflex_izq=True,
            reflex_der=True,
        )
        self.assertTrue(result["converged"])
        self.assertIsNone(result["k_eff"])
        self.assertEqual(result["mode"], "fixed_source")

    def test_mixed_boundaries_do_not_inject_flux(self):
        """Reflective left + vacuum right + no source must stay at zero."""
        result = run_config(
            NC=[20],
            NU_SIGF=[0.0],
            MODE="fixed_source",
            Q=[0.0],
            reflex_izq=True,
            reflex_der=False,
        )
        self.assertTrue(result["converged"])
        self.assertEqual(float(np.max(np.abs(result["scalar_flux"]))), 0.0)

    def test_mode_inference(self):
        """NU_SIGF>0 + no K_EFF + no MODE infers eigenvalue."""
        result = run_config(MODE=None)
        self.assertEqual(result["mode"], "eigenvalue")
        self.assertTrue(result["k_converged"])

    def test_invalid_mode_combinations(self):
        with self.assertRaises(ValueError):
            run_config(MODE="eigenvalue", Q=[1.0])
        with self.assertRaises(ValueError):
            run_config(MODE="fixed_k", K_EFF=None)
        with self.assertRaises(ValueError):
            run_config(MODE="fixed_source", NU_SIGF=[0.11])
        with self.assertRaises(ValueError):
            run_config(MODE="driven", Q=[0.0])


if __name__ == "__main__":
    unittest.main()
