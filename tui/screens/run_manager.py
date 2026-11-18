"""Run manager with live CLI output."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    LoadingIndicator,
    RichLog,
    Select,
    SelectionList,
    Static,
    Switch,
)

from ..services.config_store import list_configs
from ..services.paths import resolve_path
from ..services.results import next_result_path
from ..widgets.run_panel import RunPanel


class RunManagerPane(RunPanel, VerticalScroll):
    """Select configurations and run the 1D solver in a subprocess."""

    def compose(self) -> ComposeResult:
        yield Static("Run manager", classes="title")
        yield Horizontal(
            Button("Refresh", id="run-refresh"),
            Button("Run selected", id="run-start", variant="primary"),
            Button("Cancel", id="run-cancel", variant="error"),
            LoadingIndicator(id="run-loading"),
            classes="button-row",
        )
        yield SelectionList(id="run-configs", classes="selection-list")
        yield Horizontal(
            Label("Scheme", classes="field-label"),
            Select(
                [
                    ("From configuration", ""),
                    ("DD", "DD"),
                    ("STEP", "STEP"),
                    ("SC", "SC"),
                ],
                value="",
                allow_blank=False,
                id="run-scheme",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output JSON", classes="field-label"),
            Input(
                value=str(next_result_path()),
                placeholder="outputs/results/output_1d_XXX.json",
                id="run-output",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Excel", classes="field-label"),
            Switch(value=False, id="run-excel"),
            classes="field-row",
        )
        yield Static("", id="run-status", classes="status")
        yield RichLog(id="run-log", markup=False, wrap=True)
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self.init_run_panel()
        self.refresh_configs()

    def refresh_configs(self) -> None:
        selection = self.query_one("#run-configs", SelectionList)
        selection.clear_options()
        for path in list_configs():
            selection.add_option((path.name, str(path)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "run-refresh":
            self.refresh_configs()
        elif button == "run-start":
            self._start()
        elif button == "run-cancel":
            self.cancel_run()

    def _start(self) -> None:
        selection = self.query_one("#run-configs", SelectionList)
        selected = [Path(str(value)) for value in selection.selected]
        if not selected:
            self._set_status("Select at least one configuration.")
            return

        output_text = self.query_one("#run-output", Input).value.strip()
        output = resolve_path(output_text) if output_text else next_result_path()
        scheme_select = self.query_one("#run-scheme", Select)
        scheme = (
            None
            if scheme_select.is_blank() or not scheme_select.value
            else str(scheme_select.value)
        )
        excel = self.query_one("#run-excel", Switch).value

        self.start_run(selected, output, scheme=scheme, excel=excel)

    def on_run_complete(self, result: dict) -> None:
        code = result.get("returncode")
        output = result.get("output_path")
        if result.get("cancelled"):
            self._set_status(f"Cancelled. Partial output: {output}")
        elif code == 0:
            self._set_status(f"Finished. Output: {output}")
        else:
            self._set_status(f"Finished with code {code}. Output: {output}")
        self.query_one("#run-output", Input).value = str(next_result_path())
        self.app.refresh_all()
