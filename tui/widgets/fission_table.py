"""Editable per-zone fission table (nu*Sigma_f and optional Sigma_f)."""

from __future__ import annotations

from typing import ClassVar

from .row_table import Column, RowTable


class FissionTable(RowTable):
    """nu*Sigma_f and Sigma_f per material zone."""

    id_prefix = "fission"
    title = "Fission per zone"
    row_prefix = "Z"
    row_name = "zone"
    editable = False
    columns: ClassVar[tuple[Column, ...]] = (
        Column("nusf", "nu*Sigma_f", "0.0", kind="float"),
        Column(
            "sigmaf",
            "Sigma_f (optional)",
            "",
            kind="float",
            placeholder="blank",
            required=False,
        ),
    )

    def __init__(self, rows: list[dict] | None = None, **kwargs) -> None:
        super().__init__(rows, **kwargs)
        self._zone_count: int | None = None

    def set_zone_count(self, count: int) -> None:
        """Keep exactly one row per material zone."""
        self._zone_count = count
        if count == len(self._rows):
            return
        while len(self._rows) < count:
            self._rows.append(self._default_row())
        del self._rows[count:]
        if self.is_mounted:
            self._rebuild()

    def set_values(self, nusf: list, sigmaf: list | None = None) -> None:
        self.set_columns(nusf, sigmaf or [], minimum=self._zone_count or 0)

    def values(self) -> tuple[list[float], list[float] | None]:
        nusf, sigmaf = super().values()
        if all(value is None for value in sigmaf):
            return nusf, None
        if any(value is None for value in sigmaf):
            raise ValueError("Sigma_f: fill every zone or leave every zone blank.")
        return nusf, sigmaf
