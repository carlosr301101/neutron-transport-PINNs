"""Editable table of spatial regions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label

DEFAULT_ROW = {"cells": "1", "length": "10.0", "zone": "1", "q": "0.0"}


class RegionTable(Vertical):
    """Regions with cells, thickness, material zone and external source."""

    class Changed(Message):
        """Posted after a row is added or removed."""

        def __init__(self, table: "RegionTable") -> None:
            self.table = table
            super().__init__()

    def __init__(self, rows: list[dict] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows = [dict(row) for row in (rows or [DEFAULT_ROW])]
        self._source_visible = True

    def compose(self) -> ComposeResult:
        yield Label("Regions", classes="table-title")
        yield Horizontal(
            Label("R#", classes="cell-id"),
            Label("Cells", classes="cell-head"),
            Label("Length [cm]", classes="cell-head"),
            Label("Zone", classes="cell-head"),
            Label("Q", id="region-q-head", classes="cell-head"),
            Label("", classes="cell-del"),
            classes="table-header",
        )
        yield Container(id="region-rows")
        yield Horizontal(
            Button("+ Region", id="region-add"),
            classes="button-row",
        )

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one("#region-rows", Container)
        container.remove_children()
        rows = []
        for index, row in enumerate(self._rows):
            rows.append(
                Horizontal(
                    Label(f"R{index + 1}", classes="cell-id"),
                    Input(
                        value=row["cells"],
                        id=f"region-{index}-cells",
                        classes="cell-input",
                    ),
                    Input(
                        value=row["length"],
                        id=f"region-{index}-length",
                        classes="cell-input",
                    ),
                    Input(
                        value=row["zone"],
                        id=f"region-{index}-zone",
                        classes="cell-input",
                    ),
                    Input(
                        value=row["q"],
                        id=f"region-{index}-q",
                        classes="cell-input",
                    ),
                    Button("x", id=f"region-{index}-remove", classes="cell-del"),
                    classes="table-row",
                )
            )
        container.mount_all(rows)
        self._apply_source_visibility()

    def set_values(
        self,
        cells: list,
        lengths: list,
        zones: list,
        sources: list | None = None,
    ) -> None:
        count = max(
            len(cells) or 1,
            len(lengths) or 1,
            len(zones) or 1,
            len(sources or []) or 1,
        )
        rows = []
        for index in range(count):
            rows.append(
                {
                    "cells": str(cells[index]) if index < len(cells) else "1",
                    "length": str(lengths[index]) if index < len(lengths) else "10.0",
                    "zone": str(zones[index]) if index < len(zones) else "1",
                    "q": str(sources[index])
                    if sources and index < len(sources)
                    else "0.0",
                }
            )
        self._rows = rows
        if self.is_mounted:
            self._rebuild()

    def as_dicts(self) -> list[dict]:
        return [dict(row) for row in self._rows]

    def values(self) -> tuple[list[int], list[float], list[int], list[float]]:
        cells: list[int] = []
        lengths: list[float] = []
        zones: list[int] = []
        sources: list[float] = []
        for index, row in enumerate(self._rows):
            try:
                cells.append(int(row["cells"]))
                lengths.append(float(row["length"]))
                zones.append(int(row["zone"]))
                sources.append(float(row["q"]))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Region R{index + 1}: fill cells, length, zone and Q with numbers."
                ) from exc
        return cells, lengths, zones, sources

    def set_source_visible(self, visible: bool) -> None:
        self._source_visible = visible
        self._apply_source_visibility()

    def _apply_source_visibility(self) -> None:
        if not self.is_mounted:
            return
        try:
            self.query_one("#region-q-head", Label).display = self._source_visible
        except Exception:  # noqa: BLE001
            pass
        for index in range(len(self._rows)):
            try:
                self.query_one(
                    f"#region-{index}-q", Input
                ).display = self._source_visible
            except Exception:  # noqa: BLE001
                pass

    def add_row(self) -> None:
        self._rows.append(dict(DEFAULT_ROW))
        self._rebuild()
        self.post_message(self.Changed(self))

    def remove_row(self, index: int) -> None:
        if len(self._rows) <= 1:
            self.notify("At least one region is required.", severity="warning")
            return
        if 0 <= index < len(self._rows):
            self._rows.pop(index)
            self._rebuild()
            self.post_message(self.Changed(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if not input_id.startswith("region-"):
            return
        parts = input_id.split("-")
        if len(parts) != 3:
            return
        try:
            index = int(parts[1])
        except ValueError:
            return
        field = parts[2]
        if 0 <= index < len(self._rows) and field in self._rows[index]:
            self._rows[index][field] = event.value
            self.post_message(self.Changed(self))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id or ""
        if button == "region-add":
            self.add_row()
        elif button.startswith("region-") and button.endswith("-remove"):
            self.remove_row(int(button.split("-")[1]))
