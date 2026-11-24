"""The TUI source must be in English (labels, comments and docstrings)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("tui", "tui2d")

ACCENTS = re.compile(r"[áéíóúÁÉÍÓÚñÑ¿¡]")
SPANISH = re.compile(
    r"\b("
    r"carga|cargar|selecciona|esperando|pestaña|archivo|hijos|después|método|"
    r"refresco|consultar|todavía|vacío|composición|componer|primero|monta|"
    r"revierte|evita|mover|foco|reactive|anterior|recibir|acaba|programar|"
    r"siguiente|queda|aplica|devuelve|muestra|ejecuta|guarda|borra|añade|"
    r"ninguno|ninguna"
    r")\b",
    re.IGNORECASE,
)


class TestTuiLanguage(unittest.TestCase):
    def test_no_spanish_text_in_tui_sources(self):
        problems: list[str] = []
        for package in PACKAGES:
            for path in sorted((ROOT / package).rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                for number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if ACCENTS.search(line) or SPANISH.search(line):
                        problems.append(
                            f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
                        )
        self.assertEqual(
            problems,
            [],
            "Spanish text found in the TUI (it must be English):\n"
            + "\n".join(problems),
        )


if __name__ == "__main__":
    unittest.main()
