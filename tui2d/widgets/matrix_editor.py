"""Editable matrix (``ZMAP`` and ``QMAP``) for the 2D configuration form."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, Label, Static


class MatrixEditor(Vertical):
    """Grid of inputs with ``rows x cols`` shape.

    Widget ids are ``<prefix>-<row>-<col>``. ``kind`` is ``int`` for ``ZMAP``
    (zone indices) and ``float`` for ``QMAP`` (source values).
    """

    class Changed(Message):
        """Posted when a cell changes or the grid is resized."""

        def __init__(self, editor: MatrixEditor) -> None:
            self.editor = editor
            super().__init__()

    def __init__(
        self,
        prefix: str,
        title: str,
        kind: str,
        rows: int = 1,
        cols: int = 1,
        placeholder: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix
        self.title = title
        self.kind = kind
        self.placeholder = placeholder
        self.rows = max(1, rows)
        self.cols = max(1, cols)
        self._values: list[list[str]] = self._empty_values()

    def _empty_values(self) -> list[list[str]]:
        default = "1" if self.kind == "int" else "1.0"
        return [[default for _ in range(self.cols)] for _ in range(self.rows)]

    @property
    def grid_id(self) -> str:
        return f"{self.prefix}-grid"

    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="table-title")
        yield Static("", id=f"{self.prefix}-hint", classes="muted")
        yield Vertical(id=self.grid_id)
        self.call_after_refresh(self._rebuild)

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one(f"#{self.grid_id}", Vertical)
        container.remove_children()
        rows: list[Any] = []
        for row in range(self.rows):
            cells: list[Any] = [
                Label(f"{self.prefix.upper()} y{row + 1}", classes="matrix-label")
            ]
            for col in range(self.cols):
                cells.append(
                    Input(
                        value=self._value(row, col),
                        placeholder=self.placeholder,
                        id=f"{self.prefix}-{row}-{col}",
                        classes="matrix-cell",
                    )
                )
            rows.append(Horizontal(*cells, classes="matrix-row"))
        container.mount_all(rows)
        self.query_one(f"#{self.prefix}-hint", Static).update(
            f"{self.rows} row(s) x {self.cols} column(s); "
            "rows are Y (bottom to top), columns are X (left to right)."
        )

    def _value(self, row: int, col: int) -> str:
        try:
            return self._values[row][col]
        except IndexError:
            return "1" if self.kind == "int" else "1.0"

    def set_size(self, rows: int, cols: int) -> None:
        """Resize the grid, preserving the overlapping values."""
        rows, cols = max(1, rows), max(1, cols)
        if rows == self.rows and cols == self.cols:
            return
        old = self._values
        values = [
            [
                old[r][c]
                if r < len(old) and c < len(old[r])
                else ("1" if self.kind == "int" else "1.0")
                for c in range(cols)
            ]
            for r in range(rows)
        ]
        self.rows, self.cols = rows, cols
        self._values = values
        if self.is_mounted:
            self._rebuild()
        self.post_message(self.Changed(self))

    def set_values(self, matrix: list[list[Any]]) -> None:
        """Replace the grid with *matrix* (at least ``1x1``)."""
        rows = max(1, len(matrix))
        cols = max(1, max((len(row) for row in matrix), default=1))
        self.rows, self.cols = rows, cols
        self._values = [
            [
                str(matrix[r][c]) if r < len(matrix) and c < len(matrix[r]) else ""
                for c in range(cols)
            ]
            for r in range(rows)
        ]
        if self.is_mounted:
            self._rebuild()
        self.post_message(self.Changed(self))

    def values(self) -> list[list[Any]]:
        """Parsed matrix; raises ``ValueError`` with the cell position."""
        converter = int if self.kind == "int" else float
        parsed: list[list[Any]] = []
        for row in range(self.rows):
            parsed_row: list[Any] = []
            for col in range(self.cols):
                text = self._value(row, col).strip()
                if not text:
                    raise ValueError(
                        f"{self.prefix.upper()} y{row + 1} x{col + 1}: "
                        "value is required."
                    )
                try:
                    parsed_row.append(converter(text))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"{self.prefix.upper()} y{row + 1} x{col + 1}: "
                        "must be a number."
                    ) from exc
            parsed.append(parsed_row)
        return parsed

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if not input_id.startswith(f"{self.prefix}-"):
            return
        parts = input_id.split("-")
        if len(parts) != 3:
            return
        try:
            row, col = int(parts[1]), int(parts[2])
        except ValueError:
            return
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self._values[row][col] = event.value
            self.post_message(self.Changed(self))
