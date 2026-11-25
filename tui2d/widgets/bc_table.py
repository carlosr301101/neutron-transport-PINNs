"""Boundary-condition editor for the four sides of the 2D domain."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, Label, Select, Static

SIDES = ("left", "bottom", "right", "top")
LABELS = ("Left", "Bottom", "Right", "Top")
TYPE_OPTIONS = (
    ("Reflective (-1.0)", "reflective"),
    ("Vacuum (0.0)", "vacuum"),
    ("Incoming flux (> 0)", "incoming"),
)


class BCTable(Vertical):
    """One row per side with a type selector and an optional flux value."""

    class Changed(Message):
        """Posted when a boundary condition changes."""

        def __init__(self, table: BCTable) -> None:
            self.table = table
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._updating = False

    def compose(self) -> ComposeResult:
        yield Label("Boundary conditions", classes="table-title")
        yield Static(
            "Order: left, bottom, right, top. Reflective = -1.0, "
            "vacuum = 0.0, incoming flux > 0.",
            id="bc-hint",
            classes="muted",
        )
        for side, label in zip(SIDES, LABELS, strict=True):
            yield Horizontal(
                Label(label, classes="bc-label"),
                Select(
                    TYPE_OPTIONS,
                    value="vacuum",
                    allow_blank=False,
                    id=f"bc-{side}-type",
                ),
                Input(
                    value="",
                    placeholder="flux",
                    disabled=True,
                    id=f"bc-{side}-value",
                ),
                classes="field-row",
            )

    def set_values(self, bc: list[float]) -> None:
        """Populate the table from ``[left, bottom, right, top]``."""
        self._updating = True
        try:
            for side, value in zip(SIDES, bc, strict=True):
                select = self.query_one(f"#bc-{side}-type", Select)
                field = self.query_one(f"#bc-{side}-value", Input)
                number = float(value)
                if number == -1.0:
                    select.value = "reflective"
                    field.value = ""
                    field.disabled = True
                elif number == 0.0:
                    select.value = "vacuum"
                    field.value = ""
                    field.disabled = True
                else:
                    select.value = "incoming"
                    field.value = f"{number:g}"
                    field.disabled = False
        finally:
            self._updating = False
        self.post_message(self.Changed(self))

    def values(self) -> list[float]:
        """Return ``[left, bottom, right, top]`` from the current widgets."""
        result: list[float] = []
        for side, label in zip(SIDES, LABELS, strict=True):
            kind = str(self.query_one(f"#bc-{side}-type", Select).value)
            if kind == "reflective":
                result.append(-1.0)
            elif kind == "vacuum":
                result.append(0.0)
            else:
                text = self.query_one(f"#bc-{side}-value", Input).value.strip()
                try:
                    value = float(text)
                except ValueError as exc:
                    raise ValueError(
                        f"{label}: incoming flux must be a positive number."
                    ) from exc
                if value <= 0:
                    raise ValueError(
                        f"{label}: incoming flux must be greater than zero."
                    )
                result.append(value)
        return result

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._updating:
            return
        select_id = event.select.id or ""
        if not select_id.startswith("bc-") or not select_id.endswith("-type"):
            return
        side = select_id.split("-")[1]
        field = self.query_one(f"#bc-{side}-value", Input)
        kind = str(event.select.value)
        if kind == "incoming":
            field.disabled = False
            if not field.value.strip():
                field.value = "1.0"
        else:
            field.disabled = True
            field.value = ""
        self.post_message(self.Changed(self))

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._updating:
            return
        input_id = event.input.id or ""
        if input_id.startswith("bc-") and input_id.endswith("-value"):
            self.post_message(self.Changed(self))
