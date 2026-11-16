"""Shared editable table used by the configuration form.

``RegionTable``, ``ZoneTable`` and ``FissionTable`` differ only in their
columns and in a couple of hooks, so the row building, id conventions,
parsing and add/remove plumbing live here once.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label

from core.placeholders import is_placeholder


@dataclass(frozen=True)
class Column:
    """One editable column of a :class:`RowTable`."""

    key: str
    label: str
    default: str = ""
    kind: str = "text"  # text | int | float
    placeholder: str = ""
    required: bool = True
    head_id: str | None = None


class RowTable(Vertical):
    """Vertical table of rows built from a :class:`Column` spec.

    Ids and CSS classes are ``<id_prefix>-<row>-<column>``,
    ``<id_prefix>-<row>-remove`` and ``<id_prefix>-add``; the row container is
    ``<id_prefix>-rows``.  Keep them stable: the stylesheet and the screens
    query them directly.
    """

    id_prefix: ClassVar[str] = "row"
    title: ClassVar[str] = "Rows"
    columns: ClassVar[tuple[Column, ...]] = ()
    row_prefix: ClassVar[str] = "R"
    row_name: ClassVar[str] = "row"
    add_label: ClassVar[str] = "+ Row"
    editable: ClassVar[bool] = True
    remove_blocked_message: ClassVar[str] = "Row is in use; unlink it first."

    class Changed(Message):
        """Posted after a row is added, removed or edited."""

        def __init__(self, table: RowTable) -> None:
            self.table = table
            super().__init__()

    def __init__(
        self,
        rows: list[dict] | None = None,
        can_remove: Callable[[int], bool] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.can_remove = can_remove
        self._hidden: dict[str, bool] = {}
        self._rows = [self._normalize(row) for row in (rows or [self._default_row()])]

    # -- building ------------------------------------------------------
    @classmethod
    def _default_row(cls) -> dict[str, str]:
        return {column.key: column.default for column in cls.columns}

    def _normalize(self, row: dict) -> dict[str, str]:
        return {
            column.key: str(row.get(column.key, column.default))
            for column in self.columns
        }

    @property
    def container_id(self) -> str:
        return f"{self.id_prefix}-rows"

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="table-title")
        yield Horizontal(
            Label(f"{self.row_prefix}#", classes="cell-id"),
            *self._header_cells(),
            *(
                [Label("", classes="cell-del")]
                if self.editable
                else []
            ),
            classes="table-header",
        )
        yield Container(id=self.container_id)
        if self.editable:
            yield Horizontal(
                Button(self.add_label, id=f"{self.id_prefix}-add"),
                classes="button-row",
            )

    def _header_cells(self) -> list[Label]:
        cells: list[Label] = []
        for column in self.columns:
            classes = "cell-head"
            if self._hidden.get(column.key):
                classes += " hidden-cell"
            cells.append(Label(column.label, id=column.head_id, classes=classes))
        return cells

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one(f"#{self.container_id}", Container)
        container.remove_children()
        rows = []
        for index, row in enumerate(self._rows):
            row_widgets: list[Any] = [
                Label(f"{self.row_prefix}{index + 1}", classes="cell-id")
            ]
            for column in self.columns:
                hidden = self._hidden.get(column.key, False)
                cell = Input(
                    value=row[column.key],
                    placeholder=column.placeholder,
                    id=f"{self.id_prefix}-{index}-{column.key}",
                    classes="cell-input",
                )
                cell.display = not hidden
                row_widgets.append(cell)
            if self.editable:
                row_widgets.append(
                    Button(
                        "x",
                        id=f"{self.id_prefix}-{index}-remove",
                        classes="cell-del",
                    )
                )
            rows.append(Horizontal(*row_widgets, classes="table-row"))
        container.mount_all(rows)

    # -- data ----------------------------------------------------------
    def set_rows(self, rows: list[dict]) -> None:
        """Replace every row, keeping the current order."""
        self._rows = [self._normalize(row) for row in rows] or [self._default_row()]
        if self.is_mounted:
            self._rebuild()

    def set_columns(self, *columns_data: list, minimum: int = 0) -> None:
        """Fill the table column by column, padding missing values."""
        count = max([len(items) for items in columns_data] + [minimum, 1])
        rows: list[dict] = []
        for index in range(count):
            rows.append(
                {
                    column.key: (
                        str(items[index]) if index < len(items) else column.default
                    )
                    for column, items in zip(self.columns, columns_data)
                }
            )
        self.set_rows(rows)

    def as_dicts(self) -> list[dict]:
        return [dict(row) for row in self._rows]

    def values(self) -> tuple[list, ...]:
        """Parsed column values, in declaration order."""
        parsed: list[list] = [[] for _ in self.columns]
        for index, row in enumerate(self._rows):
            for slot, column in zip(parsed, self.columns):
                slot.append(self._convert(column, row.get(column.key, ""), index))
        return tuple(parsed)

    def _convert(self, column: Column, raw: Any, index: int) -> Any:
        text = str(raw).strip()
        where = f"{self.row_name.capitalize()} {self.row_prefix}{index + 1}"
        if not text:
            if not column.required:
                return None
            raise ValueError(f"{where}: {column.label} is required.")
        if column.kind == "text" or is_placeholder(text):
            return text
        converter = int if column.kind == "int" else float
        try:
            return converter(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where}: {column.label} must be a number.") from exc

    # -- actions -------------------------------------------------------
    def add_row(self) -> None:
        if not self.editable:
            return
        self._rows.append(self._default_row())
        self._rebuild()
        self.post_message(self.Changed(self))

    def remove_row(self, index: int) -> None:
        if not self.editable:
            return
        if len(self._rows) <= 1:
            self.notify(
                f"At least one {self.row_name} is required.", severity="warning"
            )
            return
        if self.can_remove is not None and not self.can_remove(index):
            self.notify(self.remove_blocked_message, severity="warning")
            return
        if 0 <= index < len(self._rows):
            self._rows.pop(index)
            self._rebuild()
            self.post_message(self.Changed(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        parts = input_id.split("-")
        if len(parts) != 3 or parts[0] != self.id_prefix:
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
        if button == f"{self.id_prefix}-add":
            self.add_row()
        elif button.startswith(f"{self.id_prefix}-") and button.endswith("-remove"):
            self.remove_row(int(button.split("-")[1]))

    # -- column visibility --------------------------------------------
    def set_column_visible(self, key: str, visible: bool) -> None:
        self._hidden[key] = not visible
        if not self.is_mounted:
            return
        column = next((item for item in self.columns if item.key == key), None)
        if column is not None and column.head_id:
            try:
                self.query_one(f"#{column.head_id}", Label).display = visible
            except Exception:  # noqa: BLE001 - header not mounted yet
                self.log.debug("header %s not mounted", column.head_id)
        for index in range(len(self._rows)):
            try:
                self.query_one(
                    f"#{self.id_prefix}-{index}-{key}", Input
                ).display = visible
            except Exception:  # noqa: BLE001 - row not mounted yet
                self.log.debug("cell %s-%s not mounted", index, key)
