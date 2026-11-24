"""Small editable table used by the 2D configuration form."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label


@dataclass(frozen=True)
class Column:
    """One editable column of a :class:`RowTable`."""

    key: str
    label: str
    default: str = ""
    kind: str = "text"  # text | int | float
    required: bool = True


class RowTable(Vertical):
    """Vertical table of rows built from a :class:`Column` spec.

    Widget ids are ``<prefix>-<row>-<column>``, ``<prefix>-<row>-remove`` and
    ``<prefix>-add``; the rows live in ``<prefix>-rows``.
    """

    class Changed(Message):
        """Posted after a row is added, removed or edited."""

        def __init__(self, table: RowTable) -> None:
            self.table = table
            super().__init__()

    def __init__(
        self,
        prefix: str,
        title: str,
        row_prefix: str,
        columns: tuple[Column, ...],
        min_rows: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix
        self.title = title
        self.row_prefix = row_prefix
        self.columns = columns
        self.min_rows = min_rows
        self._rows = [self._default_row()]

    # -- building ------------------------------------------------------
    def _default_row(self) -> dict[str, str]:
        return {column.key: column.default for column in self.columns}

    def _normalize(self, row: dict) -> dict[str, str]:
        return {
            column.key: str(row.get(column.key, column.default))
            for column in self.columns
        }

    @property
    def rows_id(self) -> str:
        return f"{self.prefix}-rows"

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="table-title")
        yield Horizontal(
            Label(f"{self.row_prefix}#", classes="cell-id"),
            *[Label(column.label, classes="cell-head") for column in self.columns],
            Label("", classes="cell-del"),
            classes="table-header",
        )
        yield Container(id=self.rows_id)
        yield Horizontal(
            Button(f"+ {self.row_prefix}", id=f"{self.prefix}-add"),
            classes="button-row",
        )

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one(f"#{self.rows_id}", Container)
        container.remove_children()
        rows: list[Any] = []
        for index, row in enumerate(self._rows):
            widgets: list[Any] = [
                Label(f"{self.row_prefix}{index + 1}", classes="cell-id")
            ]
            for column in self.columns:
                widgets.append(
                    Input(
                        value=row[column.key],
                        id=f"{self.prefix}-{index}-{column.key}",
                        classes="cell-input",
                    )
                )
            widgets.append(
                Button(
                    "x",
                    id=f"{self.prefix}-{index}-remove",
                    classes="cell-del",
                )
            )
            rows.append(Horizontal(*widgets, classes="table-row"))
        container.mount_all(rows)

    # -- data ----------------------------------------------------------
    def set_rows(self, rows: list[dict]) -> None:
        """Replace every row, keeping the current order."""
        self._rows = [self._normalize(row) for row in rows] or [self._default_row()]
        if self.is_mounted:
            self._rebuild()

    def as_dicts(self) -> list[dict]:
        return [dict(row) for row in self._rows]

    def values(self) -> tuple[list[Any], ...]:
        """Parsed column values, in declaration order."""
        parsed: list[list[Any]] = [[] for _ in self.columns]
        for index, row in enumerate(self._rows):
            for slot, column in zip(parsed, self.columns, strict=True):
                slot.append(self._convert(column, row.get(column.key, ""), index))
        return tuple(parsed)

    def _convert(self, column: Column, raw: Any, index: int) -> Any:
        text = str(raw).strip()
        where = f"{self.row_prefix}{index + 1}"
        if not text:
            if not column.required:
                return ""
            raise ValueError(f"{where}: {column.label} is required.")
        if column.kind == "text":
            return text
        converter = int if column.kind == "int" else float
        try:
            return converter(text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where}: {column.label} must be a number.") from exc

    # -- actions -------------------------------------------------------
    def add_row(self) -> None:
        self._rows.append(self._default_row())
        self._rebuild()
        self.post_message(self.Changed(self))

    def remove_row(self, index: int) -> None:
        if len(self._rows) <= self.min_rows:
            self.notify(
                f"At least {self.min_rows} row(s) are required.", severity="warning"
            )
            return
        if 0 <= index < len(self._rows):
            self._rows.pop(index)
            self._rebuild()
            self.post_message(self.Changed(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if not input_id.startswith(f"{self.prefix}-"):
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
        if button == f"{self.prefix}-add":
            self.add_row()
        elif button.startswith(f"{self.prefix}-") and button.endswith("-remove"):
            self.remove_row(int(button.split("-")[1]))


class ZoneTable(RowTable):
    """Material zones: optional name, ``sigma_t`` and ``sigma_s``."""

    class Changed(RowTable.Changed):
        """Posted after a zone row is added, removed or edited."""

    COLUMNS: ClassVar[tuple[Column, ...]] = (
        Column("name", "Name", "", kind="text", required=False),
        Column("sigma_t", "Sigma_t", "0.5", kind="float"),
        Column("sigma_s", "Sigma_s", "0.3", kind="float"),
    )

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "zone-table")
        super().__init__(
            prefix="zone",
            title="Material zones",
            row_prefix="Z",
            columns=self.COLUMNS,
            **kwargs,
        )


class RegionTable(RowTable):
    """Spatial regions in one direction: length [cm] and cells."""

    class Changed(RowTable.Changed):
        """Posted after a region row is added, removed or edited."""

    def __init__(self, prefix: str, title: str, **kwargs) -> None:
        kwargs.setdefault("id", f"{prefix}-table")
        super().__init__(
            prefix=prefix,
            title=title,
            row_prefix="R",
            columns=(
                Column("length", "Length [cm]", "10.0", kind="float"),
                Column("cells", "Cells", "5", kind="int"),
            ),
            **kwargs,
        )
