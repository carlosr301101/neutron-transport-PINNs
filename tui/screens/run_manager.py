"""Run manager with live CLI output."""

from __future__ import annotations

from pathlib import Path

from textual import work
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
from ..services.results import next_result_path
from ..services.runner import RunProcess


class RunManagerPane(VerticalScroll):
    """Select configurations and run the 1D solver in a subprocess."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._process: RunProcess | None = None

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

    def on_mount(self) -> None:
        self.query_one("#run-loading", LoadingIndicator).display = False
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
            self._cancel()

    def _start(self) -> None:
        selection = self.query_one("#run-configs", SelectionList)
        selected = [Path(str(value)) for value in selection.selected]
        if not selected:
            self._status("Select at least one configuration.")
            return

        output_text = self.query_one("#run-output", Input).value.strip()
        output = Path(output_text) if output_text else next_result_path()
        scheme_select = self.query_one("#run-scheme", Select)
        scheme = (
            None
            if scheme_select.is_blank() or not scheme_select.value
            else str(scheme_select.value)
        )
        excel = self.query_one("#run-excel", Switch).value

        self.query_one("#run-log", RichLog).clear()
        self.query_one("#run-status", Static).update("Running...")
        self.query_one("#run-loading", LoadingIndicator).display = True
        self.query_one("#run-start", Button).disabled = True
        self._process = RunProcess()
        self._run_worker(selected, output, scheme, excel)

    def _cancel(self) -> None:
        if self._process is not None:
            self._process.cancel()
            self._status("Cancel requested.")

    @work(thread=True, exclusive=True)
    def _run_worker(
        self,
        selected: list[Path],
        output: Path,
        scheme: str | None,
        excel: bool,
    ) -> None:
        assert self._process is not None

        def on_line(line: str) -> None:
            self.app.call_from_thread(self._append, line)

        try:
            result = self._process.run(
                selected,
                output,
                excel=excel,
                scheme=scheme,
                on_line=on_line,
            )
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(self._failed, str(exc))
            return
        self.app.call_from_thread(self._finished, result)

    def _append(self, line: str) -> None:
        self.query_one("#run-log", RichLog).write(line)

    def _status(self, message: str) -> None:
        self.query_one("#run-status", Static).update(message)

    def _reset_controls(self) -> None:
        self.query_one("#run-loading", LoadingIndicator).display = False
        self.query_one("#run-start", Button).disabled = False

    def _finished(self, result: dict) -> None:
        self._reset_controls()
        rc = result.get("returncode")
        output = result.get("output_path")
        if result.get("cancelled"):
            self._status(f"Cancelled. Partial output: {output}")
        elif rc == 0:
            self._status(f"Finished. Output: {output}")
        else:
            self._status(f"Finished with code {rc}. Output: {output}")
        self.query_one("#run-output", Input).value = str(next_result_path())
        self.app.refresh_results()

    def _failed(self, message: str) -> None:
        self._reset_controls()
        self._status(f"[red]Run failed:[/] {message}")
        self.query_one("#run-log", RichLog).write(f"ERROR: {message}")
