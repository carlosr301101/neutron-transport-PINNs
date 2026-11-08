"""Tests for `nts-1d-normalize` (post-hoc power normalization)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np

from cli.commands import cmd_run_1d
from utils import normalize_1d

CONFIG = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [10],
    "HR": [20.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.9],
    "NU_SIGF": [0.11],
    "Q": [0.0],
    "N": 2,
    "SPATIAL_SCHEME": "DD",
    "MODE": "eigenvalue",
    "NU": 2.4,
    "E_F_MEV": 200.0,
    "AREA_CM2": 1.0,
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0.0],
    "bound_right": [0.0],
}

RUN = {
    "config_name": "run_a",
    "configuration": {
        "NC": [2],
        "HR": [2.0],
        "IZL": [1],
        "SCT": [1.0],
        "SCS": [0.5],
        "NU_SIGF": [0.1],
        "NU": 2.4,
        "E_F_MEV": 200.0,
        "AREA_CM2": 1.0,
    },
    "scalar_flux": [1.0, 0.5],
    "angular_flux": [[1.0, 1.0], [0.5, 0.5]],
    "miu": [-0.57735, 0.57735],
    "omega": [1.0, 1.0],
    "k_eff": 1.01,
}


def run_solver(config: dict, output: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.json"
        path.write_text(json.dumps(config))
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cmd_run_1d(
                Namespace(
                    manual=False,
                    json=path,
                    config=None,
                    output=output,
                    forced_scheme=None,
                    excel=None,
                )
            )
    assert rc == 0
    return json.loads(output.read_text())


class TestNormalizeRun(unittest.TestCase):
    def test_scales_fluxes_and_reports_cn(self):
        import copy

        run = copy.deepcopy(RUN)
        c_n, p_unnorm = normalize_1d.normalize_run(run, 10.0)
        expected_p = (
            2.0
            * 200.0
            * 1.602176634e-13
            * (0.1 / 2.4)
            * (1.0 * 1.0 + 0.5 * 1.0)
        )
        self.assertAlmostEqual(p_unnorm, expected_p, delta=1e-24)
        self.assertAlmostEqual(c_n, 10_000.0 / expected_p, delta=1e-6)
        self.assertAlmostEqual(run["power_unnormalized"], expected_p, delta=1e-24)
        self.assertAlmostEqual(run["power_scale"], c_n, delta=1e-6)
        self.assertEqual(run["power_w"], 10_000.0)
        self.assertAlmostEqual(run["scalar_flux"][0], 1.0 * c_n, delta=1e-6)
        self.assertAlmostEqual(run["angular_flux"][0][0], 1.0 * c_n, delta=1e-6)
        self.assertEqual(run["k_eff"], 1.01)

    def test_nu_fallback(self):
        import copy

        run = copy.deepcopy(RUN)
        run["configuration"].pop("NU")
        c_n, _ = normalize_1d.normalize_run(run, 10.0, nu=2.4)
        self.assertGreater(c_n, 0.0)

    def test_missing_sigma_f_uses_default_nu(self):
        import copy

        run = copy.deepcopy(RUN)
        run["configuration"].pop("NU")
        with contextlib.redirect_stdout(io.StringIO()):
            c_n, _ = normalize_1d.normalize_run(run, 10.0)
        self.assertGreater(c_n, 0.0)

    def test_default_nu_matches_explicit(self):
        import copy

        run_default = copy.deepcopy(RUN)
        run_default["configuration"].pop("NU")
        run_explicit = copy.deepcopy(RUN)
        run_explicit["configuration"].pop("NU")
        with contextlib.redirect_stdout(io.StringIO()):
            c_default, p_default = normalize_1d.normalize_run(run_default, 10.0)
            c_explicit, p_explicit = normalize_1d.normalize_run(
                run_explicit, 10.0, nu=2.49
            )
        self.assertAlmostEqual(c_default, c_explicit, delta=1e-6)
        self.assertAlmostEqual(p_default, p_explicit, delta=1e-24)


class TestNormalizeCli(unittest.TestCase):
    def test_matches_direct_power_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp) / "base.json"
            ref_path = Path(tmp) / "ref.json"
            normalized_path = Path(tmp) / "normalized.json"

            run_solver(CONFIG, base_path)
            ref = run_solver({**CONFIG, "POWER_KW": 10.0}, ref_path)
            rc = normalize_1d.main(
                [str(base_path), "--power-kw", "10", "-o", str(normalized_path)]
            )
            self.assertEqual(rc, 0)
            normalized = json.loads(normalized_path.read_text())
            base = json.loads(base_path.read_text())["runs"][0]

        ref_run = ref["runs"][0]
        norm_run = normalized["runs"][0]

        np.testing.assert_allclose(
            np.asarray(norm_run["scalar_flux"]),
            np.asarray(ref_run["scalar_flux"]),
            rtol=1e-12,
            atol=1e-6,
        )
        np.testing.assert_allclose(
            np.asarray(norm_run["angular_flux"]),
            np.asarray(ref_run["angular_flux"]),
            rtol=1e-12,
            atol=1e-6,
        )
        self.assertEqual(norm_run["k_eff"], base["k_eff"])
        self.assertAlmostEqual(norm_run["power_w"], 10_000.0)
        self.assertAlmostEqual(
            norm_run["power_scale"] * norm_run["power_unnormalized"],
            10_000.0,
            delta=1e-6,
        )

    def test_default_output_and_run_filter(self):
        payload = {"solver": "NTS_DD_1D", "runs": [RUN, {**RUN, "config_name": "run_b"}]}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "out.json"
            source.write_text(json.dumps(payload))
            rc = normalize_1d.main(
                [str(source), "--power-kw", "10", "--run", "run_b"]
            )
            self.assertEqual(rc, 0)
            output = source.with_name("out_normalized.json")
            data = json.loads(output.read_text())
        self.assertEqual([r["config_name"] for r in data["runs"]], ["run_b"])
        self.assertIn("normalized_at", data)

    def test_power_kw_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "out.json"
            source.write_text(json.dumps({"runs": [RUN]}))
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    normalize_1d.main([str(source)])

    def test_missing_data_returns_error(self):
        run = {**RUN, "configuration": {**RUN["configuration"]}}
        run["configuration"].pop("NU")
        run["configuration"].pop("NU_SIGF")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "out.json"
            source.write_text(json.dumps({"runs": [run]}))
            with contextlib.redirect_stderr(io.StringIO()):
                rc = normalize_1d.main([str(source), "--power-kw", "10"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
