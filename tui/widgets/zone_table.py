"""Editable table of material zones."""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label

DEFAULT_ROW = {"sct": "1.0", "scs": "0.9"}


class ZoneTable(Vertical):
    """Sigma_t and Sigma_s0 per material zone."""

    class Changed(Message):
        """Posted after a row is added or removed."""

        def __init__(self, table: "ZoneTable") -> None:
            self.table = table
            super().__init__()

    def __init__(
        self,
        rows: list[dict] | None = None,
        can_remove: Callable[[int], bool] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._rows = [dict(row) for row in (rows or [DEFAULT_ROW])]
        self.can_remove = can_remove

    def compose(self) -> ComposeResult:
        yield Label("Material zones", classes="table-title")
        yield Horizontal(
            Label("Z#", classes="cell-id"),
            Label("Sigma_t", classes="cell-head"),
            Label("Sigma_s0", classes="cell-head"),
            Label("", classes="cell-del"),
            classes="table-header",
        )
        yield Container(id="zone-rows")
        yield Horizontal(
            Button("+ Zone", id="zone-add"),
            classes="button-row",
        )

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one("#zone-rows", Container)
        container.remove_children()
        rows = []
        for index, row in enumerate(self._rows):
            rows.append(
                Horizontal(
                    Label(f"Z{index + 1}", classes="cell-id"),
                    Input(
                        value=row["sct"],
                        id=f"zone-{index}-sct",
                        classes="cell-input",
                    ),
                    Input(
                        value=row["scs"],
                        id=f"zone-{index}-scs",
                        classes="cell-input",
                    ),
                    Button("x", id=f"zone-{index}-remove", classes="cell-del"),
                    classes="table-row",
                )
            )
        container.mount_all(rows)

    def set_values(self, sct: list, scs: list) -> None:
        count = max(len(sct) or 1, len(scs) or 1)
        rows = []
        for index in range(count):
            rows.append(
                {
                    "sct": str(sct[index]) if index < len(sct) else "1.0",
                    "scs": str(scs[index]) if index < len(scs) else "0.9",
                }
            )
        self._rows = rows
        if self.is_mounted:
            self._rebuild()

    def as_dicts(self) -> list[dict]:
        return [dict(row) for row in self._rows]

    def values(self) -> tuple[list[float], list[float]]:
        sct: list[float] = []
        scs: list[float] = []
        for index, row in enumerate(self._rows):
            try:
                sct.append(float(row["sct"]))
                scs.append(float(row["scs"]))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Zone Z{index + 1}: fill Sigma_t and Sigma_s0 with numbers."
                ) from exc
        return sct, scs

    @property
    def zone_count(self) -> int:
        return len(self._rows)

    def add_row(self) -> None:
        self._rows.append(dict(DEFAULT_ROW))
        self._rebuild()
        self.post_message(self.Changed(self))

    def remove_row(self, index: int) -> None:
        if len(self._rows) <= 1:
            self.notify("At least one zone is required.", severity="warning")
            return
        if self.can_remove is not None and not self.can_remove(index):
            self.notify(
                "Zone is used by a region; change the region zone first.",
                severity="warning",
            )
            return
        if 0 <= index < len(self._rows):
            self._rows.pop(index)
            self._rebuild()
            self.post_message(self.Changed(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if not input_id.startswith("zone-"):
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
        if button == "zone-add":
            self.add_row()
        elif button.startswith("zone-") and button.endswith("-remove"):
            self.remove_row(int(button.split("-")[1]))
