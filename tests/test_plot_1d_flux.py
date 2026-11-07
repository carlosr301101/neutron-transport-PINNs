"""Tests for utils.plot_1d_flux (nts-1d-plot)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt

from utils import plot_1d_flux as plot


def make_output(path: Path, n_runs: int = 2) -> None:
    config = {"NC": [4], "HR": [4.0], "N": 2}
    runs = []
    for i in range(n_runs):
        runs.append(
            {
                "config_name": f"run_{i}",
                "configuration": config,
                "scalar_flux": [1.0, 2.0, 2.0, 1.0],
                # (NTC, N): one column per direction, ordered by mu
                "angular_flux": [
                    [0.1, 0.2],
                    [0.3, 0.4],
                    [0.3, 0.4],
                    [0.1, 0.2],
                ],
                "miu": [-0.57735, 0.57735],
                "omega": [1.0, 1.0],
                "k_history": [1.1, 1.05, 1.02] if i == 0 else [],
                "mode": "eigenvalue" if i == 0 else "fixed_k",
                "k_eff": 1.02 if i == 0 else 1.0,
            }
        )
    path.write_text(json.dumps({"solver": "NTS_DD_1D", "runs": runs}))


def make_datos(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "data": [
                    {"SCS": 0.1, "flux_0": 1.0, "flux_3": 0.5, "k_eff": 1.02},
                    {"SCS": 0.2, "flux_0": 0.9, "flux_3": 0.4, "k_eff": 1.03},
                ]
            }
        )
    )


def run_plot(argv: list[str], stdout: io.StringIO | None = None) -> int:
    """Run the plot CLI capturing console output (tests assert behaviour)."""
    with contextlib.redirect_stdout(stdout or io.StringIO()):
        with contextlib.redirect_stderr(io.StringIO()):
            return plot.main(argv)


class TestPlot1DFlux(unittest.TestCase):
    def test_list_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            out = io.StringIO()
            rc = run_plot(["-r", str(result), "--list-runs"], stdout=out)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("[0] run_0", text)
        self.assertIn("[1] run_1", text)
        self.assertIn("k_eff=1.02000000", text)

    def test_multiple_runs_require_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = run_plot(["-r", str(result), "--kind", "scalar"])
        self.assertEqual(rc, 2)

    def test_scalar_selected_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            output = Path(tmp) / "scalar.png"
            make_output(result, n_runs=2)
            rc = run_plot(
                [
                    "-r", str(result), "--kind", "scalar",
                    "--run", "run_1", "-o", str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_scalar_all_overlays(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            output = Path(tmp) / "scalar_all.png"
            make_output(result, n_runs=2)
            rc = run_plot(
                [
                    "-r", str(result), "--kind", "scalar",
                    "--run", "all", "-o", str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_angular_single_axes_and_legends(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            run = plot.load_output(result)[0]
            with patch.object(plot, "_save") as save:
                plot.plot_angular(run, None, Path(tmp) / "angular.png")
                fig = save.call_args.args[0]
                ax = fig.axes[0]
                self.assertEqual(len(ax.lines), 2)
                labels = [line.get_label() for line in ax.lines]
                self.assertIn("μ=-0.577350", labels)
                self.assertIn("μ=+0.577350", labels)
                self.assertNotEqual(
                    ax.lines[0].get_color(), ax.lines[1].get_color()
                )
                plt.close(fig)

    def test_angular_selected_directions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            output = Path(tmp) / "angular.png"
            make_output(result, n_runs=2)
            rc = run_plot(
                [
                    "-r", str(result), "--kind", "angular",
                    "--run", "run_0", "--directions", "1",
                    "-o", str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_angular_all_runs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = run_plot(
                    ["-r", str(result), "--kind", "angular", "--run", "all"]
                )
        self.assertEqual(rc, 2)

    def test_k_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            output = Path(tmp) / "khistory.png"
            make_output(result, n_runs=2)
            rc = run_plot(
                [
                    "-r", str(result), "--kind", "k-history",
                    "--run", "run_0", "-o", str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_k_history_empty_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = run_plot(
                    [
                        "-r", str(result), "--kind", "k-history",
                        "--run", "run_1",
                    ]
                )
        self.assertEqual(rc, 2)

    def test_legacy_datos_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            datos = Path(tmp) / "datos.json"
            output = Path(tmp) / "scs.png"
            make_datos(datos)
            rc = run_plot(
                ["-i", str(datos), "--x", "k_eff", "-o", str(output)]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())

    def test_invalid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = run_plot(
                    ["-r", str(result), "--kind", "scalar", "--run", "nope"]
                )
        self.assertEqual(rc, 2)

    def test_mutually_exclusive_sources(self):
        with self.assertRaises(SystemExit):
            run_plot(["-r", "a.json", "-i", "b.json"])

    def test_directions_only_for_angular(self):
        with self.assertRaises(SystemExit):
            run_plot(
                [
                    "-r", "a.json", "--kind", "scalar",
                    "--directions", "0",
                ]
            )


class TestEnglishLabelsAndMessages(unittest.TestCase):
    """nts-1d-plot must render English axes, titles and legends."""

    def _capture_figure(self, fn, *args):
        with patch.object(plot, "_save") as save:
            fn(*args)
            return save.call_args.args[0]

    def test_scalar_single_run_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            runs = plot.load_output(result)
            fig = self._capture_figure(
                plot.plot_scalar, [runs[0]], Path(tmp) / "scalar.png"
            )
            ax = fig.axes[0]
            self.assertEqual(ax.get_xlabel(), "x [cm]")
            self.assertEqual(ax.get_ylabel(), "Scalar flux")
            self.assertTrue(ax.get_title().startswith("Scalar flux — run_0"))
            plt.close(fig)

    def test_scalar_overlay_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            runs = plot.load_output(result)
            fig = self._capture_figure(
                plot.plot_scalar, runs, Path(tmp) / "scalar_all.png"
            )
            ax = fig.axes[0]
            self.assertEqual(ax.get_title(), "Scalar flux vs x")
            labels = [line.get_label() for line in ax.lines]
            self.assertTrue(any(label.startswith("run_0") for label in labels))
            self.assertTrue(any(label.startswith("run_1") for label in labels))
            plt.close(fig)

    def test_angular_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            run = plot.load_output(result)[0]
            fig = self._capture_figure(
                plot.plot_angular, run, None, Path(tmp) / "angular.png"
            )
            ax = fig.axes[0]
            self.assertEqual(ax.get_xlabel(), "x [cm]")
            self.assertEqual(ax.get_ylabel(), "Angular flux ψ(x,μ)")
            self.assertTrue(ax.get_title().startswith("Angular flux — run_0"))
            self.assertEqual(ax.get_legend().get_title().get_text(), "Direction μ")
            labels = [line.get_label() for line in ax.lines]
            self.assertIn("μ=-0.577350", labels)
            self.assertIn("μ=+0.577350", labels)
            plt.close(fig)

    def test_k_history_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "output_1d_test.json"
            make_output(result, n_runs=2)
            runs = plot.load_output(result)
            fig = self._capture_figure(
                plot.plot_k_history, [runs[0]], Path(tmp) / "khistory.png"
            )
            ax = fig.axes[0]
            self.assertEqual(ax.get_xlabel(), "Outer iteration")
            self.assertEqual(ax.get_ylabel(), "k_eff")
            self.assertEqual(ax.get_title(), "k_eff history")
            labels = [line.get_label() for line in ax.lines]
            self.assertIn("run_0", labels)
            self.assertTrue(any(label.startswith("run_0 final = ") for label in labels))
            plt.close(fig)

    def test_scs_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            datos = Path(tmp) / "datos.json"
            make_datos(datos)
            fig = self._capture_figure(
                plot.plot_datos, datos, Path(tmp) / "scs.png", "SCS"
            )
            first = fig.axes[0]
            self.assertEqual(first.get_title(), "Scalar Flux vs SCS (Position 0)")
            self.assertEqual(first.get_ylabel(), "Scalar Flux")
            legend_labels = [t.get_text() for t in first.get_legend().get_texts()]
            self.assertEqual(legend_labels, ["Flux at position 0"])
            self.assertEqual(fig.axes[-1].get_xlabel(), "SCS")
            plt.close(fig)

    def test_angular_legacy_schema(self):
        """Old files (NTP, N/2) still plot with the weighted-sum label."""
        run = {
            "config_name": "old",
            "configuration": {"NC": [4], "HR": [4.0], "N": 2},
            "angular_flux": [
                [0.1, 0.2],
                [0.3, 0.4],
                [0.3, 0.4],
                [0.1, 0.2],
                [0.0, 0.0],
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fig = self._capture_figure(
                plot.plot_angular, run, None, Path(tmp) / "legacy.png"
            )
            ax = fig.axes[0]
            self.assertEqual(ax.get_ylabel(), "Angular flux  ω_m(ψ⁺ + ψ⁻)")
            labels = [line.get_label() for line in ax.lines]
            self.assertEqual(labels, ["direction 0", "direction 1"])
            plt.close(fig)

    def test_module_has_no_spanish_text(self):
        """Static guard: no Spanish words or accents in any string literal."""
        import ast
        import re

        spanish = re.compile(
            r"\b(flujo|escalar|posici[oó]n|iteraci[oó]n|historial|leyenda|"
            r"disponibles|fichero|direcci[oó]n|impuesto|advertencia)\b",
            re.IGNORECASE,
        )
        accented = re.compile(r"[áéíóúüñÁÉÍÓÚÜÑ¿¡]")
        source = Path(plot.__file__).read_text()
        offenders = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if accented.search(node.value) or spanish.search(node.value):
                offenders.append((node.lineno, node.value))
        self.assertEqual(offenders, [], f"Spanish text in plot module: {offenders}")


if __name__ == "__main__":
    unittest.main()
