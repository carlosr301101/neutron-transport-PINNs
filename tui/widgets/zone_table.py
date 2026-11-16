"""Editable table of material zones."""

from __future__ import annotations

from typing import ClassVar

from .row_table import Column, RowTable


class ZoneTable(RowTable):
    """Sigma_t and Sigma_s0 per material zone."""

    class Changed(RowTable.Changed):
        """Posted after a zone row is added, removed or edited."""

    id_prefix = "zone"
    title = "Material zones"
    row_prefix = "Z"
    row_name = "zone"
    add_label = "+ Zone"
    remove_blocked_message = "Zone is used by a region; change the region zone first."
    columns: ClassVar[tuple[Column, ...]] = (
        Column("sct", "Sigma_t", "1.0", kind="float"),
        Column("scs", "Sigma_s0", "0.9", kind="float"),
    )

    def set_values(self, sct: list, scs: list) -> None:
        self.set_columns(sct, scs)

    @property
    def zone_count(self) -> int:
        return len(self._rows)
