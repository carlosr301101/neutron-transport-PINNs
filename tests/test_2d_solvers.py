"""Smoke tests for the five 2D C solvers.

Each test runs the real binaries in ``solvers/runners`` (or the directory in
``NTS_SOLVERS_DIR``) against an ``input.txt`` produced by ``InputBuilder``.
The checks are numerical, not bit-exact:

- the solver exits cleanly and returns ``STATUS = 0``;
- ``ITER``, ``CPU`` and the ``MFLUX``/``MFLOW``/``XFLOW``/``YFLOW`` shapes
  match ``doc/2D_SOLVERS_CONTRACT.md``;
- the flux is finite and positive;
- a uniform problem is symmetric, and a reflective boundary raises the flux
  on the expected side (this catches a swapped ``BC`` order).

The five binaries are executed once per class; individual tests only assert.
Rebuild them from the repository root with::

    make -C solvers

On Windows use ``solvers/build_windows.ps1`` (MSYS2/MinGW-w64).
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.config import SimulationConfig
from core.input_builder import InputBuilder
from utils.paths import AVAILABLE_SOLVERS, get_solver_path

# Small enough to finish in about one second per solver.
N = 4
CELLS = 4
LENGTH = 10.0
TOL = 1e-4


def solver_config(bc, qmap_value=1.0, sigma_t=0.5, sigma_s=0.3, n=N):
    """Return a uniform 2x2-region problem with the requested BC."""
    return SimulationConfig(
        N=n,
        NZ=1,
        zones=[{"sigma_t": sigma_t, "sigma_s": sigma_s}],
        NR_X=2,
        XDOM=[{"length": LENGTH, "nodes": CELLS}] * 2,
        NR_Y=2,
        YDOM=[{"length": LENGTH, "nodes": CELLS}] * 2,
        ZMAP=[[1, 1], [1, 1]],
        QMAP=[[qmap_value, qmap_value], [qmap_value, qmap_value]],
        BC=bc,
        TOL=TOL,
    )


def run_binary(solver: str, input_path: Path, timeout: int = 300) -> dict:
    """Run one solver and return the parsed JSON output."""
    binary = get_solver_path(solver)
    proc = subprocess.run(
        [str(binary), str(input_path)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"{solver} exited with code {proc.returncode}: {proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"{solver} did not return valid JSON: {proc.stdout[:300]!r}"
        ) from exc


def row_means(mflux):
    """Return the mean of every row (one value per y index)."""
    width = len(mflux[0])
    return [sum(row) / width for row in mflux]


def col_means(mflux):
    """Return the mean of every column (one value per x index)."""
    height = len(mflux)
    width = len(mflux[0])
    return [sum(row[i] for row in mflux) / height for i in range(width)]


class TestSolvers(unittest.TestCase):
    """Run the five binaries once and validate their output."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls._tmp.name)

        cls.inputs = {}
        for name, bc in (
            ("vacuum", [0.0, 0.0, 0.0, 0.0]),
            ("left", [-1.0, 0.0, 0.0, 0.0]),
            ("bottom", [0.0, -1.0, 0.0, 0.0]),
        ):
            path = cls.tmpdir / f"{name}.txt"
            InputBuilder(solver_config(bc)).save(str(path))
            cls.inputs[name] = path

        cls.results = {}
        cls.errors = {}
        cls.missing = []
        for solver in AVAILABLE_SOLVERS:
            try:
                get_solver_path(solver)
            except FileNotFoundError:
                cls.missing.append(solver)
                continue
            try:
                cls.results[solver] = run_binary(solver, cls.inputs["vacuum"])
            except Exception as exc:  # noqa: BLE001 - report, do not abort
                cls.errors[solver] = str(exc)

        # Two extra runs with NTS_DD for the boundary-condition order test.
        cls.bc_results = {}
        if "NTS_DD" in cls.results:
            for name in ("left", "bottom"):
                cls.bc_results[name] = run_binary("NTS_DD", cls.inputs[name])

        cls.addClassCleanup(cls._tmp.cleanup)

    def result(self, solver: str) -> dict:
        """Return a solver result, skipping when the binary is unavailable."""
        if solver in self.errors:
            self.fail(self.errors[solver])
        if solver not in self.results:
            self.skipTest(f"{solver} binary not found")
        return self.results[solver]

    def test_binaries_are_available(self):
        """All five binaries must be present and executable."""
        if self.missing:
            self.fail(f"missing solver binaries: {', '.join(self.missing)}")
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                path = get_solver_path(solver)
                self.assertTrue(path.is_file(), path)

    def test_status_and_iterations(self):
        """Each solver converges and reports iterations."""
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                data = self.result(solver)
                self.assertEqual(data.get("STATUS"), 0, data)
                self.assertGreater(data["ITER"], 0)

    def test_cpu_time_is_non_negative(self):
        """``CPU`` is a finite, non-negative number of seconds."""
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                data = self.result(solver)
                cpu = float(data["CPU"])
                self.assertTrue(math.isfinite(cpu), cpu)
                self.assertGreaterEqual(cpu, 0.0, f"{solver}: CPU={cpu}")

    def test_mflux_shape_and_values(self):
        """``MFLUX`` is a finite, positive ``ntc_y x ntc_x`` matrix."""
        expected_y = 2 * CELLS
        expected_x = 2 * CELLS
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                data = self.result(solver)
                mflux = data["MFLUX"]
                self.assertIsInstance(mflux, list)
                self.assertEqual(len(mflux), expected_y)
                for row in mflux:
                    self.assertEqual(len(row), expected_x)
                    for value in row:
                        self.assertTrue(math.isfinite(value))
                        self.assertGreater(value, 0.0)

    def test_angular_flow_shapes(self):
        """``MFLOW``/``XFLOW``/``YFLOW`` follow the contract shapes."""
        directions = N * (N + 2) // 2
        ny = nx = 2 * CELLS
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                data = self.result(solver)

                mflow = data["MFLOW"]
                self.assertEqual(len(mflow), directions)
                self.assertEqual(len(mflow[0]), ny)
                self.assertEqual(len(mflow[0][0]), nx)

                xflow = data["XFLOW"]
                self.assertEqual(len(xflow), directions)
                self.assertEqual(len(xflow[0]), ny)
                self.assertEqual(len(xflow[0][0]), nx + 1)

                yflow = data["YFLOW"]
                self.assertEqual(len(yflow), directions)
                self.assertEqual(len(yflow[0]), ny + 1)
                self.assertEqual(len(yflow[0][0]), nx)

    def test_vacuum_problem_is_symmetric(self):
        """A uniform source with vacuum boundaries is symmetric in x and y."""
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                mflux = self.result(solver)["MFLUX"]
                ny, nx = len(mflux), len(mflux[0])
                scale = max(max(row) for row in mflux)

                horizontal = max(
                    abs(mflux[j][i] - mflux[j][nx - 1 - i])
                    for j in range(ny)
                    for i in range(nx)
                )
                vertical = max(
                    abs(mflux[j][i] - mflux[ny - 1 - j][i])
                    for j in range(ny)
                    for i in range(nx)
                )
                self.assertLess(horizontal / scale, 1e-5)
                self.assertLess(vertical / scale, 1e-5)

    def test_solvers_agree_on_total_flux(self):
        """All five schemes solve the same problem within a few percent."""
        reference = self.result("NTS_DD")["MFLUX"]
        ref_mean = sum(sum(row) for row in reference) / (
            len(reference) * len(reference[0])
        )
        for solver in AVAILABLE_SOLVERS:
            with self.subTest(solver=solver):
                mflux = self.result(solver)["MFLUX"]
                mean = sum(sum(row) for row in mflux) / (
                    len(mflux) * len(mflux[0])
                )
                self.assertAlmostEqual(mean / ref_mean, 1.0, delta=0.10)

    def test_left_reflective_raises_left_edge(self):
        """``BC = [-1, 0, 0, 0]`` must reflect on the left side."""
        if "left" not in self.bc_results:
            self.skipTest("NTS_DD binary not found")
        mflux = self.bc_results["left"]["MFLUX"]
        cols = col_means(mflux)
        rows = row_means(mflux)
        self.assertGreater(cols[0], cols[-1] * 1.2, cols)
        # y remains vacuum on both sides: symmetric rows.
        self.assertAlmostEqual(rows[0] / rows[-1], 1.0, delta=1e-3)

    def test_bottom_reflective_raises_bottom_edge(self):
        """``BC = [0, -1, 0, 0]`` must reflect on the bottom side."""
        if "bottom" not in self.bc_results:
            self.skipTest("NTS_DD binary not found")
        mflux = self.bc_results["bottom"]["MFLUX"]
        cols = col_means(mflux)
        rows = row_means(mflux)
        self.assertGreater(rows[0], rows[-1] * 1.2, rows)
        # x remains vacuum on both sides: symmetric columns.
        self.assertAlmostEqual(cols[0] / cols[-1], 1.0, delta=1e-3)


class TestSolverValidation(unittest.TestCase):
    """The C readers must reject inputs that violate the contract."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls._tmp.name)
        cls.addClassCleanup(cls._tmp.cleanup)

    def _write(self, name: str, text: str) -> Path:
        path = self.tmpdir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_invalid_boundary_condition_is_rejected(self):
        try:
            get_solver_path("NTS_DD")
        except FileNotFoundError:
            self.skipTest("NTS_DD binary not found")

        valid = InputBuilder(solver_config([0.0, 0.0, 0.0, 0.0])).build()
        bad_bc = valid.replace(
            "0.0 0.0 0.0 0.0", "-0.5 0.0 0.0 0.0"
        )
        data = run_binary("NTS_DD", self._write("bad_bc.txt", bad_bc))
        self.assertEqual(data, {"STATUS": 2})

    def test_odd_quadrature_order_is_rejected(self):
        try:
            get_solver_path("NTS_DD")
        except FileNotFoundError:
            self.skipTest("NTS_DD binary not found")

        valid = InputBuilder(solver_config([0.0, 0.0, 0.0, 0.0])).build()
        lines = valid.splitlines()
        lines[0] = "3"
        data = run_binary("NTS_DD", self._write("bad_n.txt", "\n".join(lines)))
        self.assertEqual(data, {"STATUS": 2})

    def test_missing_argument_reports_status_one(self):
        try:
            binary = get_solver_path("NTS_DD")
        except FileNotFoundError:
            self.skipTest("NTS_DD binary not found")

        proc = subprocess.run(
            [str(binary)], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout), {"STATUS": 1})


if __name__ == "__main__":
    unittest.main()
