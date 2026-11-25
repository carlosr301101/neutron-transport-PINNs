"""Proportional 2D drawing of the domain coloured by material zone.

The map is a raster of the physical domain: region lengths in X and Y set the
proportion of the drawing, and ``ZMAP`` decides the colour of each region.
Terminal characters are roughly twice as tall as they are wide, so the number
of rows is ``cols * (Ly/Lx) * CHAR_ASPECT``; a 20x10 cm domain therefore draws
twice as wide as tall instead of looking square.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static

PALETTE = (
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#b07aa1",
    "#76b7b2",
    "#edc948",
    "#ff9da7",
    "#9c755f",
)

# Height/width ratio of one terminal cell in pixels.
CHAR_ASPECT = 0.5


class DomainMap(Static):
    """Draw the X/Y regions proportionally and colour them by ``ZMAP``."""

    MAX_COLS = 46
    MIN_COLS = 12
    MAX_ROWS = 18
    MIN_ROWS = 4

    def __init__(self, **kwargs) -> None:
        super().__init__("No domain yet.", **kwargs)
        self.last_plain = "No domain yet."
        self.last_rows = 0
        self.last_cols = 0
        self.last_ratio = 0.0

    # -- public API ----------------------------------------------------
    def set_data(
        self,
        xdom: list[dict[str, Any]],
        ydom: list[dict[str, Any]],
        zmap: list[list[int]],
        zones: list[dict[str, Any]],
        bc: list[float] | None = None,
    ) -> None:
        """Redraw the map from region, zone-map and boundary data."""
        try:
            text, rows, cols, ratio = self._render_domain(xdom, ydom, zmap, zones, bc)
        except Exception as exc:  # noqa: BLE001 - keep the TUI alive
            text = Text(f"Invalid domain: {exc}", style="red")
            rows = cols = 0
            ratio = 0.0

        self.last_plain = text.plain
        self.last_rows, self.last_cols, self.last_ratio = rows, cols, ratio
        if self.is_mounted:
            self.update(text)

    # -- rendering -----------------------------------------------------
    @staticmethod
    def _lengths(regions: list[dict[str, Any]]) -> list[float]:
        values: list[float] = []
        for region in regions:
            try:
                value = float(region.get("length", 0.0))
            except (TypeError, ValueError):
                value = 0.0
            values.append(max(value, 0.0))
        return values

    @classmethod
    def grid_shape(cls, total_x: float, total_y: float) -> tuple[int, int]:
        """Return ``(rows, cols)`` for the drawing, preserving proportions."""
        ratio = total_y / total_x if total_x > 0 else 1.0
        cols = cls.MAX_COLS
        rows = round(cols * ratio * CHAR_ASPECT)
        if rows > cls.MAX_ROWS:
            rows = cls.MAX_ROWS
            cols = round(rows / (ratio * CHAR_ASPECT)) if ratio > 0 else cls.MAX_COLS
        elif rows < cls.MIN_ROWS:
            rows = cls.MIN_ROWS
            cols = round(rows / (ratio * CHAR_ASPECT)) if ratio > 0 else cls.MAX_COLS
        cols = max(cls.MIN_COLS, min(cls.MAX_COLS, cols))
        rows = max(cls.MIN_ROWS, min(cls.MAX_ROWS, rows))
        return rows, cols

    @staticmethod
    def _indices(lengths: list[float], count: int) -> list[int]:
        """Region index for each of *count* cells along one axis."""
        total = sum(lengths)
        if total <= 0 or count <= 0:
            return [0] * max(count, 0)
        edges: list[float] = []
        accumulated = 0.0
        for length in lengths:
            accumulated += length
            edges.append(accumulated / total)
        result: list[int] = []
        for cell in range(count):
            position = (cell + 0.5) / count
            for index, edge in enumerate(edges):
                if position <= edge:
                    result.append(index)
                    break
            else:
                result.append(len(lengths) - 1)
        return result

    def _render_domain(
        self,
        xdom: list[dict[str, Any]],
        ydom: list[dict[str, Any]],
        zmap: list[list[int]],
        zones: list[dict[str, Any]],
        bc: list[float] | None,
    ) -> tuple[Text, int, int, float]:
        x_lengths = self._lengths(xdom)
        y_lengths = self._lengths(ydom)
        total_x = sum(x_lengths)
        total_y = sum(y_lengths)
        if not x_lengths or not y_lengths or total_x <= 0 or total_y <= 0:
            raise ValueError("regions need a positive length")

        rows, cols = self.grid_shape(total_x, total_y)
        x_regions = self._indices(x_lengths, cols)
        y_regions = self._indices(y_lengths, rows)  # bottom to top

        text = Text()
        for row in range(rows):
            # Display row 0 is the top of the domain.
            ry = y_regions[rows - 1 - row]
            for col in range(cols):
                rx = x_regions[col]
                zone = self._zone_at(zmap, ry, rx)
                color = (
                    PALETTE[(zone - 1) % len(PALETTE)] if zone >= 1 else "grey37"
                )
                vertical_edge = col > 0 and x_regions[col] != x_regions[col - 1]
                horizontal_edge = (
                    row > 0
                    and y_regions[rows - 1 - row]
                    != y_regions[rows - 1 - (row - 1)]
                )
                if vertical_edge and horizontal_edge:
                    glyph = "┼"
                elif vertical_edge:
                    glyph = "│"
                elif horizontal_edge:
                    glyph = "─"
                else:
                    glyph = " "
                style = f"on {color} black" if glyph != " " else f"on {color}"
                text.append(glyph, style=style)
            text.append("\n")

        text.append("\n")
        text.append(
            f"X: {total_x:g} cm · {len(xdom)} region(s) · "
            f"{sum(_cells(region) for region in xdom)} cells  |  "
            f"Y: {total_y:g} cm · {len(ydom)} region(s) · "
            f"{sum(_cells(region) for region in ydom)} cells\n",
            style="dim",
        )
        ratio = total_y / total_x
        text.append(
            f"Drawing {cols}x{rows} cells · physical aspect {ratio:.3f} "
            f"({ratio * CHAR_ASPECT:.3f} rows per column)\n",
            style="dim",
        )

        if zones:
            for index, zone in enumerate(zones, start=1):
                color = PALETTE[(index - 1) % len(PALETTE)]
                name = zone.get("name") or f"Zone {index}"
                text.append("██ ", style=color)
                text.append(
                    f"{name} (sigma_t={zone.get('sigma_t', '?')}, "
                    f"sigma_s={zone.get('sigma_s', '?')})   ",
                    style="bold",
                )
            text.append("\n")

        if bc is not None and len(bc) == 4:
            parts = []
            for label, value in zip(("L", "B", "R", "T"), bc, strict=True):
                number = float(value)
                if number == -1.0:
                    parts.append(f"{label}=Reflective")
                elif number == 0.0:
                    parts.append(f"{label}=Vacuum")
                else:
                    parts.append(f"{label}=Incoming({number:g})")
            text.append("BC: " + " · ".join(parts), style="bold")

        return text, rows, cols, ratio

    @staticmethod
    def _zone_at(zmap: list[list[int]], row: int, col: int) -> int:
        try:
            value = int(zmap[row][col])
        except (IndexError, TypeError, ValueError):
            return 0
        return value


def _cells(region: dict[str, Any]) -> int:
    try:
        return max(0, int(region.get("cells", 0)))
    except (TypeError, ValueError):
        return 0
