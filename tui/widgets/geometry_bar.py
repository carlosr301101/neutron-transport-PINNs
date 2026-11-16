"""Graphical strip of the 1D region layout, coloured by material zone."""

from __future__ import annotations

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

WIDTH = 64


class GeometryBar(Static):
    """Render regions as proportional coloured blocks."""

    def __init__(self, **kwargs) -> None:
        super().__init__("No regions.", **kwargs)
        self.last_plain = "No regions."

    def set_data(
        self,
        regions: list[dict],
        zones: list[dict],
    ) -> None:
        """Update the bar from region and zone dictionaries."""
        if not regions:
            self.last_plain = "No regions."
            if self.is_mounted:
                self.update(self.last_plain)
            return

        lengths: list[float] = []
        for region in regions:
            try:
                value = float(region.get("length", 0.0))
            except (TypeError, ValueError):
                value = 0.0
            lengths.append(max(value, 0.0))

        total = sum(lengths)
        if total <= 0:
            lengths = [1.0] * len(regions)
            total = float(len(regions))

        blocks: list[Text] = []
        for index, region in enumerate(regions):
            width = max(3, round(WIDTH * lengths[index] / total))
            try:
                zone_id = int(region.get("zone", 0))
            except (TypeError, ValueError):
                zone_id = 0
            valid = 1 <= zone_id <= len(zones)
            background = PALETTE[(zone_id - 1) % len(PALETTE)] if valid else "grey37"
            label = f"R{index + 1}"
            if width < len(label) + 2:
                label = ""
            blocks.append(Text(f"{label:^{width}}", style=f"on {background}"))

        text = Text()
        for block in blocks:
            text.append_text(block)
        text.append("\n")

        for index, region in enumerate(regions):
            text.append(
                f"R{index + 1}: {region.get('cells', '?')} cells, "
                f"{region.get('length', '?')} cm, Z{region.get('zone', '?')}\n",
                style="dim",
            )

        text.append("\n")
        for index, zone in enumerate(zones):
            text.append(
                f"Z{index + 1}: Sigma_t={zone.get('sct', '?')}  "
                f"Sigma_s0={zone.get('scs', '?')}\n",
                style="bold",
            )

        self.last_plain = text.plain
        if self.is_mounted:
            self.update(text)
