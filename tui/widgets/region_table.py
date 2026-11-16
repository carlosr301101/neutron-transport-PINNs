"""Editable table of spatial regions."""

from __future__ import annotations

from typing import ClassVar

from .row_table import Column, RowTable


class RegionTable(RowTable):
    """Regions with cells, thickness, material zone and external source."""

    class Changed(RowTable.Changed):
        """Posted after a region row is added, removed or edited."""

    id_prefix = "region"
    title = "Regions"
    row_prefix = "R"
    row_name = "region"
    add_label = "+ Region"
    columns: ClassVar[tuple[Column, ...]] = (
        Column("cells", "Cells", "1", kind="int"),
        Column("length", "Length [cm]", "10.0", kind="float"),
        Column("zone", "Zone", "1", kind="int"),
        Column("q", "Q", "0.0", kind="float", head_id="region-q-head"),
    )

    def set_values(
        self,
        cells: list,
        lengths: list,
        zones: list,
        sources: list | None = None,
    ) -> None:
        self.set_columns(cells, lengths, zones, sources or [])

    def set_source_visible(self, visible: bool) -> None:
        self.set_column_visible("q", visible)
