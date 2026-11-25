"""Read a solver ``input.txt`` back into geometry information.

Results files (``output_*.json``) do not carry the spatial grid, so plotting
needs the original input to place the flux on physical axes.  This module
parses the canonical format documented in ``doc/2D_SOLVERS_CONTRACT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SolverInput:
    """Subset of a solver input file needed to reconstruct the grid."""

    N: int
    NZ: int
    zones: list[tuple[float, float]]
    NR_X: int
    XDOM: list[tuple[float, int]]
    NR_Y: int
    YDOM: list[tuple[float, int]]
    ZMAP: list[list[int]] = field(default_factory=list)
    QMAP: list[list[float]] = field(default_factory=list)
    BC: list[float] = field(default_factory=list)
    TOL: float = 0.0

    @property
    def total_nodes_x(self) -> int:
        return sum(nodes for _, nodes in self.XDOM)

    @property
    def total_nodes_y(self) -> int:
        return sum(nodes for _, nodes in self.YDOM)

    @property
    def total_length_x(self) -> float:
        return sum(length for length, _ in self.XDOM)

    @property
    def total_length_y(self) -> float:
        return sum(length for length, _ in self.YDOM)

    @property
    def extent(self) -> tuple[float, float, float, float]:
        """Return ``(xmin, xmax, ymin, ymax)`` in cm for ``imshow``."""
        return (0.0, self.total_length_x, 0.0, self.total_length_y)


class _Tokens:
    def __init__(self, text: str):
        self._items = text.split()
        self._pos = 0

    def take(self, count: int = 1) -> list[str]:
        chunk = self._items[self._pos : self._pos + count]
        if len(chunk) != count:
            raise ValueError(
                "input file ended early: expected "
                f"{count} value(s), found {len(chunk)}"
            )
        self._pos += count
        return chunk

    def int(self) -> int:
        raw = self.take(1)[0]
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"expected an integer, got {raw!r}") from exc

    def float(self) -> float:
        raw = self.take(1)[0]
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"expected a number, got {raw!r}") from exc


def parse_input_text(text: str) -> SolverInput:
    """Parse the text of a solver input file."""
    tokens = _Tokens(text)

    N = tokens.int()
    NZ = tokens.int()
    zones = [(tokens.float(), tokens.float()) for _ in range(NZ)]

    NR_X = tokens.int()
    XDOM = [(tokens.float(), tokens.int()) for _ in range(NR_X)]

    NR_Y = tokens.int()
    YDOM = [(tokens.float(), tokens.int()) for _ in range(NR_Y)]

    ZMAP = [[tokens.int() for _ in range(NR_X)] for _ in range(NR_Y)]
    QMAP = [[tokens.float() for _ in range(NR_X)] for _ in range(NR_Y)]
    BC = [tokens.float() for _ in range(4)]
    TOL = tokens.float()

    return SolverInput(
        N=N,
        NZ=NZ,
        zones=zones,
        NR_X=NR_X,
        XDOM=XDOM,
        NR_Y=NR_Y,
        YDOM=YDOM,
        ZMAP=ZMAP,
        QMAP=QMAP,
        BC=BC,
        TOL=TOL,
    )


def read_input(path: str | Path) -> SolverInput:
    """Read and parse a solver input file."""
    return parse_input_text(Path(path).read_text(encoding="utf-8"))
