"""Tests for the DD / STEP / SC spatial discretization schemes.

Run from the repository root:

    uv run nts-test
"""

from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

import numpy as np

from solvers.runners.NTS_DD_1D import (
    Config,
    Method,
    Runner,
    cell_average,
    cell_out,
    method_from_name,
    theta_step_characteristic,
)

BASE = {
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


def build_config(**overrides) -> Config:
    cfg = dict(BASE)
    cfg.update(overrides)
    with contextlib.redirect_stdout(io.StringIO()):
        return Config(manual=False, **cfg)


def run_config(**overrides) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        conf = build_config(**overrides)
        return Runner(conf)()


def reference_average(method, psi_in, psi_out, sigma_t, dx, mu):
    """Independent re-implementation of the scheme averages (test oracle)."""
    if method is Method.DD:
        return 0.5 * (psi_in + psi_out)
    if method is Method.STEP:
        return psi_out
    alpha = sigma_t * dx / abs(mu)
    theta = theta_step_characteristic(alpha)
    return 0.5 * (1.0 + theta) * psi_out + 0.5 * (1.0 - theta) * psi_in


class TestMethodSelection(unittest.TestCase):
    def test_default_is_dd(self):
        conf = build_config()
        self.assertEqual(conf.SPATIAL_SCHEME, "DD")
        self.assertIs(conf.method, Method.DD)

    def test_names_are_normalised(self):
        for name, expected in [
            ("dd", Method.DD),
            ("Step", Method.STEP),
            (" sc ", Method.STEP_CHARACTERISTIC),
            ("STEP_CHARACTERISTIC", Method.STEP_CHARACTERISTIC),
        ]:
            self.assertIs(method_from_name(name), expected)

    def test_invalid_scheme_rejected(self):
        with self.assertRaises(ValueError):
            build_config(SPATIAL_SCHEME="nope")
        with self.assertRaises(ValueError):
            method_from_name("nope")

    def test_scheme_and_method_cannot_diverge(self):
        conf = build_config(SPATIAL_SCHEME="SC")
        self.assertIs(conf.method, Method.STEP_CHARACTERISTIC)
        # The string is the single source of truth; method follows it.
        conf.SPATIAL_SCHEME = "STEP"
        self.assertIs(conf.method, Method.STEP)
        # An invalid string fails loudly instead of silently keeping DD.
        conf.SPATIAL_SCHEME = "garbage"
        with self.assertRaises(ValueError):
            _ = conf.method

    def test_as_dict_round_trip(self):
        conf = build_config(SPATIAL_SCHEME="SC")
        payload = conf.as_dict()
        self.assertEqual(payload["SPATIAL_SCHEME"], "SC")
        restored = build_config(**payload)
        self.assertIs(restored.method, Method.STEP_CHARACTERISTIC)
        self.assertEqual(restored.SPATIAL_SCHEME, "SC")

    def test_theta_sc_shape_matches_sweep_directions(self):
        conf = build_config()
        self.assertEqual(conf.theta_sc.shape, (conf.NTC, conf.N_HALF))
        for k in (0, conf.NTC // 2, conf.NTC - 1):
            for m in range(conf.N_HALF):
                alpha = conf.sigma_t_vec[k] * conf.dx_vec[k] / conf.miu_m[m]
                self.assertAlmostEqual(
                    conf.theta_sc[k, m],
                    theta_step_characteristic(alpha),
                    delta=1e-15,
                )

    def test_manual_wizard_accepts_scheme(self):
        inputs = [
            "1", "1", "20", "20", "1", "1.0", "0.9",
            "", "SC", "n", "1.0", "n", "n", "0 0 0 0", "0 0 0 0",
        ]
        with patch("builtins.input", side_effect=inputs):
            with contextlib.redirect_stdout(io.StringIO()):
                conf = Config(manual=True)
                result = Runner(conf)()
        self.assertEqual(conf.SPATIAL_SCHEME, "SC")
        self.assertIs(conf.method, Method.STEP_CHARACTERISTIC)
        self.assertTrue(result["converged"])
        self.assertEqual(result["spatial_scheme"], "SC")


class TestTheta(unittest.TestCase):
    def test_zero_optical_thickness(self):
        self.assertEqual(theta_step_characteristic(0.0), 0.0)

    def test_negative_optical_thickness_rejected(self):
        with self.assertRaises(ValueError):
            theta_step_characteristic(-1e-9)
        with self.assertRaises(ValueError):
            theta_step_characteristic(float("-inf"))

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            theta_step_characteristic(float("nan"))
        self.assertEqual(theta_step_characteristic(float("inf")), 1.0)

    def test_series_limit_for_tiny_alpha(self):
        # theta = alpha/6 - alpha^3/360 + ...; for tiny alpha the series is
        # far more accurate than the closed form (which cancels).
        for alpha in (1e-9, 1e-7, 1e-6, 1e-4):
            expected = alpha / 6.0
            self.assertAlmostEqual(
                theta_step_characteristic(alpha), expected, delta=1e-6 * expected
            )

    def test_series_matches_exact_formula(self):
        # The closed form loses ~eps*(2/alpha) to cancellation, so the
        # tolerance is scaled accordingly.
        for alpha in (9e-4, 5e-3, 1e-2, 0.1, 0.5, 1.0):
            exact = 1.0 / np.tanh(0.5 * alpha) - 2.0 / alpha
            tolerance = 50.0 * np.finfo(float).eps * (2.0 / alpha) + 1e-12
            self.assertAlmostEqual(
                theta_step_characteristic(alpha), exact, delta=tolerance
            )

    def test_continuity_at_series_threshold(self):
        below = theta_step_characteristic(1e-3 - 1e-12)
        above = theta_step_characteristic(1e-3 + 1e-12)
        self.assertLess(abs(above - below), 1e-12)

    def test_finite_and_monotone(self):
        alphas = np.logspace(-8, 4, 500)
        values = np.array([theta_step_characteristic(a) for a in alphas])
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertTrue(np.all(values >= 0.0))
        self.assertTrue(np.all(values < 1.0))
        self.assertTrue(np.all(np.diff(values) > 0.0))


class TestCellKernels(unittest.TestCase):
    def test_cell_balance_all_methods(self):
        """a*(psi_out-psi_in) + Sigma_t*psi_bar = S for every scheme."""
        rng = np.random.default_rng(20261103)
        for method in Method:
            worst = 0.0
            for _ in range(400):
                psi_in = rng.uniform(0.0, 5.0)
                source = rng.uniform(0.0, 3.0)
                sigma_t = rng.uniform(0.0, 5.0)
                dx = rng.uniform(1e-4, 2.0)
                mu = rng.uniform(1e-3, 1.0)

                psi_out = cell_out(psi_in, source, sigma_t, dx, mu, method)
                avg = cell_average(psi_in, psi_out, sigma_t, dx, mu, method)
                residual = (
                    (mu / dx) * (psi_out - psi_in) + sigma_t * avg - source
                )
                worst = max(worst, abs(residual) / max(1.0, abs(source)))

            self.assertLess(worst, 1e-9, f"{method} balance residual {worst:.3e}")

    def test_cell_average_matches_kernel(self):
        """cell_average must agree with the average implied by the sweep."""
        rng = np.random.default_rng(7)
        for method in Method:
            for _ in range(200):
                psi_in = rng.uniform(0.0, 5.0)
                source = rng.uniform(0.0, 3.0)
                sigma_t = rng.uniform(0.1, 5.0)
                dx = rng.uniform(1e-3, 2.0)
                mu = rng.uniform(1e-3, 1.0)

                psi_out = cell_out(psi_in, source, sigma_t, dx, mu, method)
                got = cell_average(psi_in, psi_out, sigma_t, dx, mu, method)
                expected = reference_average(
                    method, psi_in, psi_out, sigma_t, dx, mu
                )
                self.assertAlmostEqual(got, expected, delta=1e-12 * max(1.0, abs(got)))

    def test_sc_reduces_to_dd_for_thin_cells(self):
        # theta -> 0: both the outgoing flux and the average match DD.
        sigma_t, dx, mu = 1.0, 1e-9, 1.0
        dd_out = cell_out(0.7, 0.3, sigma_t, dx, mu, Method.DD)
        sc_out = cell_out(0.7, 0.3, sigma_t, dx, mu, Method.STEP_CHARACTERISTIC)
        self.assertAlmostEqual(sc_out, dd_out, delta=1e-9)
        dd_avg = cell_average(0.7, dd_out, sigma_t, dx, mu, Method.DD)
        sc_avg = cell_average(
            0.7, sc_out, sigma_t, dx, mu, Method.STEP_CHARACTERISTIC
        )
        self.assertAlmostEqual(sc_avg, dd_avg, delta=1e-9)

    def test_sc_average_tends_to_step_for_thick_cells(self):
        # theta -> 1, so psi_bar -> psi_out (the STEP convention).  The
        # outgoing fluxes themselves do not coincide: for an opaque cell
        # SC gives S/Sigma_t while STEP gives S/(a+Sigma_t).
        sigma_t, dx, mu = 1e6, 1.0, 1.0
        psi_out = cell_out(1.0, 0.0, sigma_t, dx, mu, Method.STEP)
        sc_avg = cell_average(
            1.0, psi_out, sigma_t, dx, mu, Method.STEP_CHARACTERISTIC
        )
        self.assertAlmostEqual(sc_avg, psi_out, delta=1e-5)

    def test_sc_average_is_convex_combination(self):
        # For 0 <= theta <= 1 the SC average lies between the DD average
        # and the outgoing flux (STEP convention).
        rng = np.random.default_rng(11)
        for _ in range(200):
            psi_in = rng.uniform(0.0, 5.0)
            source = rng.uniform(0.0, 3.0)
            sigma_t = rng.uniform(0.1, 5.0)
            dx = rng.uniform(1e-3, 2.0)
            mu = rng.uniform(1e-3, 1.0)
            psi_out = cell_out(psi_in, source, sigma_t, dx, mu, Method.DD)
            dd_avg = cell_average(psi_in, psi_out, sigma_t, dx, mu, Method.DD)
            sc_avg = cell_average(
                psi_in, psi_out, sigma_t, dx, mu, Method.STEP_CHARACTERISTIC
            )
            low, high = sorted((dd_avg, psi_out))
            self.assertGreaterEqual(sc_avg, low - 1e-12)
            self.assertLessEqual(sc_avg, high + 1e-12)

    def test_mu_sign_is_normalised(self):
        for method in Method:
            pos = cell_out(1.0, 0.5, 1.0, 0.2, 0.5, method)
            neg = cell_out(1.0, 0.5, 1.0, 0.2, -0.5, method)
            self.assertAlmostEqual(pos, neg, delta=1e-15)

    def test_zero_mu_rejected(self):
        with self.assertRaises(ValueError):
            cell_out(1.0, 0.5, 1.0, 0.2, 0.0, Method.DD)
        with self.assertRaises(ValueError):
            cell_average(1.0, 0.9, 1.0, 0.2, 0.0, Method.DD)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            cell_out(1.0, 0.5, 1.0, 0.2, 0.5, "NOPE")
        with self.assertRaises(ValueError):
            cell_average(1.0, 0.9, 1.0, 0.2, 0.5, "NOPE")

    def test_no_artificial_positivity(self):
        """Thick cells keep each scheme's natural sign (no clipping)."""
        # alpha = Sigma_t*dx/mu = 50, pure attenuation (S=0).
        dd_out = cell_out(1.0, 0.0, 1.0, 1.0, 0.02, Method.DD)
        step_out = cell_out(1.0, 0.0, 1.0, 1.0, 0.02, Method.STEP)
        sc_out = cell_out(1.0, 0.0, 1.0, 1.0, 0.02, Method.STEP_CHARACTERISTIC)
        self.assertLess(dd_out, 0.0)
        self.assertGreater(step_out, 0.0)
        self.assertTrue(np.isfinite(sc_out))


class TestSolverIntegration(unittest.TestCase):
    def test_dd_regression_benchmark(self):
        """DD must reproduce the pre-refactor results (1.0266764379)."""
        result = run_config()
        self.assertTrue(result["k_converged"])
        self.assertEqual(result["iteration"], 999)
        self.assertAlmostEqual(result["k_eff"], 1.0266764379437188, delta=1e-12)
        self.assertAlmostEqual(
            result["k_balance"], 1.0266775219239312, delta=1e-12
        )
        phi = np.asarray(result["scalar_flux"])
        self.assertAlmostEqual(float(phi[0]), 0.10320820280696363, delta=1e-12)
        self.assertAlmostEqual(float(phi[50]), 1.0, delta=1e-12)
        self.assertAlmostEqual(float(phi[99]), 0.10320820280696363, delta=1e-12)
        self.assertAlmostEqual(float(phi.sum()), 67.70760151718076, delta=1e-10)

    def test_dd_explicit_scheme_matches_default(self):
        default = run_config()
        explicit = run_config(SPATIAL_SCHEME="DD")
        self.assertEqual(default["k_eff"], explicit["k_eff"])
        np.testing.assert_array_equal(
            default["scalar_flux"], explicit["scalar_flux"]
        )

    def test_reflective_infinite_medium_all_schemes(self):
        """No leakage: k_eff = nu*Sigma_f/Sigma_a for every scheme."""
        for scheme in ("DD", "STEP", "SC"):
            result = run_config(
                SPATIAL_SCHEME=scheme,
                NC=[20],
                SCT=[1.0],
                SCS=[0.5],
                NU_SIGF=[0.3],
                reflex_izq=True,
                reflex_der=True,
            )
            self.assertTrue(result["k_converged"], scheme)
            self.assertAlmostEqual(result["k_eff"], 0.6, delta=1e-5)
            self.assertAlmostEqual(result["k_balance"], 0.6, delta=1e-5)

    def test_benchmark_all_schemes(self):
        dd = run_config()
        step = run_config(SPATIAL_SCHEME="STEP")
        sc = run_config(SPATIAL_SCHEME="SC")
        for result in (dd, step, sc):
            self.assertTrue(result["k_converged"])
            self.assertAlmostEqual(
                result["k_eff"], result["k_balance"], delta=1e-4
            )
        # DD is the reference; SC is second order and stays close, STEP is
        # first order and is deliberately allowed a larger deviation.
        self.assertAlmostEqual(dd["k_eff"], 1.026676, delta=2e-4)
        self.assertLess(abs(sc["k_eff"] - dd["k_eff"]), 1e-3)
        self.assertLess(abs(step["k_eff"] - dd["k_eff"]), 2e-2)

    def test_solver_level_cell_balance_all_schemes(self):
        """Converged sweep satisfies the per-cell balance for every scheme."""
        for scheme in ("DD", "STEP", "SC"):
            cfg = dict(BASE)
            cfg.update(
                {
                    "SPATIAL_SCHEME": scheme,
                    "NC": [40],
                    "Q": [0.2],
                    "MODE": "fixed_k",
                    "K_EFF": 1.4,
                }
            )
            with contextlib.redirect_stdout(io.StringIO()):
                conf = Config(manual=False, epsilon=1e-8, **cfg)
                result = Runner(conf)()
            self.assertTrue(result["converged"], scheme)

            phi = np.asarray(result["scalar_flux"])
            source = (
                0.5 * (conf.q_ext_vec + conf.sigma_s_vec * phi)
                + 0.5 * conf.nu_sigma_f_vec * phi / result["k_eff"]
            )
            right = np.asarray(result["PSI_RIGHT"])
            left = np.asarray(result["PSI_LEFT"])
            method = conf.method

            worst = 0.0
            for k in range(conf.NTC):
                for m in range(conf.N_HALF):
                    mu = abs(conf.miu_m[m])
                    a = mu / conf.dx_vec[k]
                    st = conf.sigma_t_vec[k]
                    avg_r = reference_average(
                        method, right[k, m], right[k + 1, m], st, conf.dx_vec[k], mu
                    )
                    avg_l = reference_average(
                        method, left[k + 1, m], left[k, m], st, conf.dx_vec[k], mu
                    )
                    worst = max(
                        worst,
                        abs(a * (right[k + 1, m] - right[k, m]) + st * avg_r - source[k]),
                        abs(a * (left[k, m] - left[k + 1, m]) + st * avg_l - source[k]),
                    )
            self.assertLess(worst, 1e-6, f"{scheme} solver balance {worst:.3e}")

    def test_fixed_source_vacuum_and_reflective_all_schemes(self):
        for scheme in ("DD", "STEP", "SC"):
            vacuum = run_config(
                SPATIAL_SCHEME=scheme,
                NC=[20],
                SCS=[0.5],
                NU_SIGF=[0.0],
                Q=[1.0],
                MODE="fixed_source",
            )
            self.assertTrue(vacuum["converged"], scheme)
            self.assertIsNone(vacuum["k_eff"])
            phi_vac = np.asarray(vacuum["scalar_flux"])
            self.assertTrue(np.all(np.isfinite(phi_vac)))
            self.assertGreater(float(np.max(phi_vac)), 0.0)

            reflective = run_config(
                SPATIAL_SCHEME=scheme,
                NC=[20],
                SCS=[0.9],
                NU_SIGF=[0.0],
                Q=[1.0],
                MODE="fixed_source",
                reflex_izq=True,
                reflex_der=True,
            )
            self.assertTrue(reflective["converged"], scheme)
            self.assertIsNone(reflective["k_eff"])
            phi_ref = np.asarray(reflective["scalar_flux"])
            # Symmetric slab with symmetric boundaries: phi(x) = phi(L-x).
            np.testing.assert_allclose(phi_ref, phi_ref[::-1], rtol=1e-6, atol=1e-9)
            # Reflective boundaries cannot lose neutrons: higher flux than
            # the equivalent vacuum problem.
            self.assertGreater(float(np.mean(phi_ref)), float(np.mean(phi_vac)))


if __name__ == "__main__":
    unittest.main()
