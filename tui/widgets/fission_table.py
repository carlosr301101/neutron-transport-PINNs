"""Editable per-zone fission table (nu*Sigma_f and optional Sigma_f)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Label

DEFAULT_ROW = {"nusf": "0.0", "sigmaf": ""}


class FissionTable(Vertical):
    """nu*Sigma_f and Sigma_f per material zone."""

    def __init__(self, rows: list[dict] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows = [dict(row) for row in (rows or [DEFAULT_ROW])]

    def compose(self) -> ComposeResult:
        yield Label("Fission per zone", classes="table-title")
        yield Horizontal(
            Label("Z#", classes="cell-id"),
            Label("nu*Sigma_f", classes="cell-head"),
            Label("Sigma_f (optional)", classes="cell-head"),
            classes="table-header",
        )
        yield Container(id="fission-rows")

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        if not self.is_mounted:
            return
        container = self.query_one("#fission-rows", Container)
        container.remove_children()
        rows = []
        for index, row in enumerate(self._rows):
            rows.append(
                Horizontal(
                    Label(f"Z{index + 1}", classes="cell-id"),
                    Input(
                        value=row["nusf"],
                        id=f"fission-{index}-nusf",
                        classes="cell-input",
                    ),
                    Input(
                        value=row["sigmaf"],
                        placeholder="blank",
                        id=f"fission-{index}-sigmaf",
                        classes="cell-input",
                    ),
                    classes="table-row",
                )
            )
        container.mount_all(rows)

    def set_zone_count(self, count: int) -> None:
        if count == len(self._rows):
            return
        while len(self._rows) < count:
            self._rows.append(dict(DEFAULT_ROW))
        del self._rows[count:]
        if self.is_mounted:
            self._rebuild()

    def set_values(self, nusf: list, sigmaf: list | None) -> None:
        count = max(len(nusf), len(sigmaf or []), len(self._rows), 1)
        rows = []
        for index in range(count):
            rows.append(
                {
                    "nusf": str(nusf[index]) if index < len(nusf) else "0.0",
                    "sigmaf": (
                        str(sigmaf[index])
                        if sigmaf is not None and index < len(sigmaf)
                        else ""
                    ),
                }
            )
        self._rows = rows
        if self.is_mounted:
            self._rebuild()

    def values(self) -> tuple[list[float], list[float] | None]:
        nusf: list[float] = []
        sigmaf: list[float | None] = []
        for index, row in enumerate(self._rows):
            try:
                nusf.append(float(row["nusf"]))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Zone Z{index + 1}: fill nu*Sigma_f with a number."
                ) from exc
            text = row["sigmaf"].strip()
            if not text:
                sigmaf.append(None)
                continue
            try:
                sigmaf.append(float(text))
            except ValueError as exc:
                raise ValueError(
                    f"Zone Z{index + 1}: Sigma_f must be a number or blank."
                ) from exc

        if all(value is None for value in sigmaf):
            return nusf, None
        if any(value is None for value in sigmaf):
            raise ValueError("Sigma_f: fill every zone or leave every zone blank.")
        return nusf, [float(value) for value in sigmaf]

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id or ""
        if not input_id.startswith("fission-"):
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
