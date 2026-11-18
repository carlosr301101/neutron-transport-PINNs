"""Regression tests for the ASCII console fallback (PowerShell/cp1252)."""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from utils.console import SafeConsole, ascii_text, emit, use_ascii

ROOT = Path(__file__).resolve().parents[1]

CONFIG = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [10],
    "HR": [10.0],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [0.5],
    "NU_SIGF": [0.0],
    "Q": [1.0],
    "N": 2,
    "SPATIAL_SCHEME": "DD",
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [0],
    "bound_right": [0],
    "MODE": "fixed_source",
}


def _clean_env(**overrides: str) -> dict[str, str]:
    """Return os.environ without the console flags, plus overrides."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"NTS_ASCII", "NTS_UNICODE"}
    }
    env.update(overrides)
    return env


class TestAsciiText(unittest.TestCase):
    def test_checkmark_becomes_ascii(self):
        self.assertEqual(
            ascii_text("✓ Completed 1 run(s)."),
            "OK Completed 1 run(s).",
        )

    def test_other_glyphs(self):
        self.assertEqual(ascii_text("✗ Error"), "X Error")
        self.assertEqual(ascii_text("• item"), "- item")
        self.assertEqual(ascii_text("→ next"), "-> next")
        self.assertEqual(ascii_text("Σt"), "Sigmat")
        self.assertEqual(ascii_text("μ+"), "mu+")
        self.assertEqual(ascii_text("k ≈ 1.0"), "k ~= 1.0")

    def test_ascii_text_is_idempotent(self):
        plain = "OK Completed 1 run(s)."
        self.assertEqual(ascii_text(plain), plain)


class TestAsciiModeSelection(unittest.TestCase):
    def test_nts_ascii_forces_ascii(self):
        with mock.patch.dict(os.environ, _clean_env(NTS_ASCII="1"), clear=True):
            self.assertTrue(use_ascii())

    def test_nts_unicode_forces_unicode(self):
        with mock.patch.dict(os.environ, _clean_env(NTS_UNICODE="1"), clear=True):
            self.assertFalse(use_ascii())

    def test_unicode_wins_over_ascii(self):
        env = _clean_env(NTS_ASCII="1", NTS_UNICODE="1")
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(use_ascii())


class TestSafeConsole(unittest.TestCase):
    def test_checkmark_survives_cp1252_stream(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252", newline="")
        with mock.patch.dict(os.environ, _clean_env(NTS_ASCII="1"), clear=True):
            SafeConsole(file=stream).print("✓ Completed 1 run(s).")
        stream.flush()
        self.assertEqual(
            buffer.getvalue().decode("cp1252"),
            "OK Completed 1 run(s).\n",
        )

    def test_emit_checkmark_survives_cp1252_stream(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252", newline="")
        with mock.patch.dict(os.environ, _clean_env(NTS_ASCII="1"), clear=True):
            emit("✓ Plot saved", file=stream)
        stream.flush()
        self.assertEqual(
            buffer.getvalue().decode("cp1252"),
            "OK Plot saved\n",
        )


class TestCliUnderCp1252(unittest.TestCase):
    def _run(self, home: str, *args: str) -> subprocess.CompletedProcess:
        env = _clean_env(
            PYTHONIOENCODING="cp1252",
            NTS_HOME=home,
            PYTHONPATH=str(ROOT),
        )
        return subprocess.run(
            [sys.executable, "-m", "cli.main", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=False,
        )

    def test_status_does_not_crash(self):
        with tempfile.TemporaryDirectory() as home:
            proc = self._run(home, "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(b"UnicodeEncodeError", proc.stderr)
        self.assertNotIn("✓".encode(), proc.stdout)
        self.assertIn(b"Solvers:", proc.stdout)

    def test_run_1d_completed_line_is_ascii(self):
        with tempfile.TemporaryDirectory() as home:
            config = Path(home) / "config.json"
            config.write_text(json.dumps(CONFIG))
            output = Path(home) / "output.json"
            proc = self._run(
                home,
                "run-1d",
                "--json",
                str(config),
                "-o",
                str(output),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn(b"UnicodeEncodeError", proc.stderr)
            self.assertIn(b"OK Completed 1 run(s).", proc.stdout)
            self.assertNotIn(b"? Completed", proc.stdout)
            self.assertNotIn("✓".encode(), proc.stdout)


RUNTIME_DIRS = ("cli", "utils", "solvers", "core", "skills")


def _string_constants(node: ast.AST):
    """Yield every string literal inside *node*, including f-string parts."""
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            yield child.value


class TestNoRawPrintWithNonAscii(unittest.TestCase):
    """Guard against print("✓ ...") bypassing the ASCII fallback."""

    def test_runtime_print_calls_are_ascii(self):
        offenders = []
        for directory in RUNTIME_DIRS:
            for path in (ROOT / directory).rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                tree = ast.parse(
                    path.read_text(encoding="utf-8"), filename=str(path)
                )
                for node in ast.walk(tree):
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "print"
                    ):
                        continue
                    for arg in node.args:
                        for text in _string_constants(arg):
                            if any(ord(char) > 127 for char in text):
                                offenders.append(
                                    f"{path.relative_to(ROOT)}:{node.lineno}"
                                )
        self.assertEqual(offenders, [], f"non-ASCII print(): {offenders}")


if __name__ == "__main__":
    unittest.main()