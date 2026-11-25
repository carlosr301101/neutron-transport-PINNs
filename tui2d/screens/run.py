"""Run manager for the 2D C solvers."""

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
)

from tui.services.paths import resolve_path

from ..models import DEFAULT_SOLVER, SOLVER_NAMES, build_preview
from ..services import config_store, results
from ..services.runner import SolverRunner


class Run2DPane(VerticalScroll):
    """Select configurations and run a 2D solver in subprocesses."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._runner: SolverRunner | None = None
        self._shutting_down = False
        self._last_output: Path | None = None
        self._auto_output = True
        self._pending_auto = True
        self._updating = False

    def compose(self) -> ComposeResult:
        yield Static("2D run manager", classes="title")
        yield Horizontal(
            Button("Refresh", id="run2d-refresh"),
            Button("Run selected", id="run2d-start", variant="primary"),
            Button("Cancel", id="run2d-cancel", variant="error"),
            Button("Results", id="run2d-results"),
            Button("Plot latest", id="run2d-plots"),
            LoadingIndicator(id="run2d-loading"),
            classes="button-row",
        )
        yield SelectionList(id="run2d-configs", classes="selection-list")
        yield Horizontal(
            Label("Solver", classes="field-label"),
            Select(
                [(name, name) for name in SOLVER_NAMES],
                value=DEFAULT_SOLVER,
                allow_blank=False,
                id="run2d-solver",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Workers", classes="field-label"),
            Select(
                [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")],
                value="1",
                allow_blank=False,
                id="run2d-workers",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output", classes="field-label"),
            Input(
                value=str(results.next_output_path()),
                placeholder="blank = auto: outputs/results/output_NNN.json",
                id="run2d-output-path",
            ),
            classes="field-row",
        )
        yield Static("", id="run2d-status", classes="status")
        yield Static(
            "Last output: none yet.",
            id="run2d-last-output",
            classes="muted",
            markup=False,
        )
        yield Static("", id="run2d-preview", classes="preview-text", markup=False)
        yield RichLog(id="run2d-log", markup=False, wrap=True)
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self._set_loading(False)
        self._set_busy(False)
        self._set_output_buttons(False)
        self.refresh_files()

    # -- state ---------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._runner is not None

    def refresh_files(self) -> None:
        """Reload configs and the default output path (tab activation)."""
        self.refresh_configs()
        self.refresh_output_path()

    def refresh_configs(self) -> None:
        selection = self.query_one("#run2d-configs", SelectionList)
        selected = {str(value) for value in selection.selected}
        selection.clear_options()
        paths = config_store.list_configs()
        values = {str(path) for path in paths}
        for path in paths:
            selection.add_option((path.name, str(path)))
        for value in selected:
            if value in values:
                selection.select(value)
        self._update_preview()

    def refresh_output_path(self) -> None:
        """Keep the prefilled output path in sync unless edited by the user."""
        if not self._auto_output:
            return
        self._updating = True
        try:
            self.query_one("#run2d-output-path", Input).value = str(
                results.next_output_path()
            )
        finally:
            self._updating = False

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        self._update_preview()
        self.refresh_output_path()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._updating:
            return
        if event.input.id == "run2d-output-path":
            self._auto_output = not event.value.strip()

    def _selected_paths(self) -> list[Path]:
        selection = self.query_one("#run2d-configs", SelectionList)
        return [Path(str(value)) for value in selection.selected]

    def _update_preview(self) -> None:
        paths = self._selected_paths()
        preview = self.query_one("#run2d-preview", Static)
        if not paths:
            preview.update("Select one or more configurations to preview input.txt.")
            return
        try:
            config = config_store.load_config(paths[0])
            text = build_preview(config, max_lines=20)
        except Exception as exc:  # noqa: BLE001
            text = f"# cannot build input.txt: {exc}"
        preview.update(f"Preview for {paths[0].name}\n{text}")

    # -- actions -------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "run2d-refresh":
            self.refresh_files()
        elif button == "run2d-start":
            self._start()
        elif button == "run2d-cancel":
            self.cancel_run()
        elif (
            button == "run2d-results"
            and self._last_output is not None
            and hasattr(self.app, "show_results")
        ):
            self.app.show_results(self._last_output)
        elif (
            button == "run2d-plots"
            and self._last_output is not None
            and hasattr(self.app, "set_plot_source")
        ):
            self.app.set_plot_source(self._last_output)

    def _start(self) -> None:
        paths = self._selected_paths()
        if not paths:
            self._status("Select at least one configuration.")
            return
        if self._runner is not None:
            self._status("A run is already in progress.")
            return

        solver = str(self.query_one("#run2d-solver", Select).value)
        workers = int(str(self.query_one("#run2d-workers", Select).value))
        output_text = self.query_one("#run2d-output-path", Input).value.strip()
        output_path: Path | None = None
        if output_text:
            output_path = resolve_path(output_text)
            if output_path.exists() and output_path.is_dir():
                self._status("Output must be a file path, not a directory.")
                return

        self._pending_auto = self._auto_output or output_path is None
        self.query_one("#run2d-log", RichLog).clear()
        self._last_output = None
        self._set_output_buttons(False)
        self.query_one("#run2d-last-output", Static).update("")
        self._status("Running...")
        self._set_loading(True)
        self._set_busy(True)
        self._runner = SolverRunner()
        self._run_worker(paths, solver, workers, output_path)

    def cancel_run(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
            self._status("Cancel requested.")

    def on_unmount(self) -> None:
        self._shutting_down = True
        if self._runner is not None:
            self._runner.cancel()
        self._runner = None

    # -- worker --------------------------------------------------------
    @work(thread=True, exclusive=True)
    def _run_worker(
        self,
        paths: list[Path],
        solver: str,
        workers: int,
        output_path: Path | None,
    ) -> None:
        runner = self._runner
        if runner is None:
            return

        def on_event(line: str) -> None:
            self._post(self._append, line)

        try:
            outcomes = runner.run(
                paths,
                solver,
                workers,
                on_event,
                output_path=output_path,
            )
        except Exception as exc:  # noqa: BLE001 - shown in the status line
            self._post(self._failed, str(exc))
            return
        self._post(self._finish, outcomes)

    def _post(self, callback, *args) -> None:
        if self._shutting_down:
            return
        try:
            self.app.call_from_thread(callback, *args)
        except RuntimeError:
            self._shutting_down = True

    def _append(self, line: str) -> None:
        if self.is_mounted:
            self.query_one("#run2d-log", RichLog).write(line)

    def _finish(self, outcomes) -> None:
        if self._shutting_down or not self.is_mounted:
            return
        self._runner = None
        self._set_loading(False)
        self._set_busy(False)
        ok = sum(1 for outcome in outcomes if outcome.ok)
        failed = len(outcomes) - ok
        cancelled = any(outcome.cancelled for outcome in outcomes)
        prefix = "Cancelled" if cancelled else "Finished"
        self._status(f"{prefix}: {ok} ok, {failed} failed.")
        self._last_output = next(
            (
                outcome.output
                for outcome in outcomes
                if outcome.ok and outcome.output is not None
            ),
            None,
        )
        self._set_output_buttons(self._last_output is not None)
        if self._last_output is not None:
            self.query_one("#run2d-last-output", Static).update(
                f"Last output: {self._last_output}"
            )
            self._append(f"Output: {self._last_output}")
        else:
            self.query_one("#run2d-last-output", Static).update(
                "No output was written; check the log above."
            )
        self._reflect_output_path()
        self._append(self._status_text(outcomes))
        if hasattr(self.app, "refresh_all"):
            self.app.refresh_all()

    def _reflect_output_path(self) -> None:
        """Show the path actually used; keep auto mode for the next run."""
        self._updating = True
        try:
            field = self.query_one("#run2d-output-path", Input)
            if self._last_output is not None and not self._pending_auto:
                field.value = str(self._last_output)
                self._auto_output = False
            elif self._pending_auto:
                field.value = str(results.next_output_path())
                self._auto_output = True
        finally:
            self._updating = False

    @staticmethod
    def _status_text(outcomes) -> str:
        lines = []
        for outcome in outcomes:
            if outcome.ok:
                target = f" -> {outcome.output}" if outcome.output else ""
                lines.append(
                    f"OK {outcome.config.name}: STATUS={outcome.status} "
                    f"ITER={outcome.iterations} CPU={outcome.cpu}{target}"
                )
            else:
                reason = outcome.error or f"STATUS={outcome.status}"
                lines.append(f"FAIL {outcome.config.name}: {reason}")
        return "\n".join(lines)

    def _failed(self, message: str) -> None:
        if self._shutting_down or not self.is_mounted:
            return
        self._runner = None
        self._set_loading(False)
        self._set_busy(False)
        self._set_output_buttons(False)
        self._status(f"[red]Run failed:[/] {message}")
        self.query_one("#run2d-last-output", Static).update(
            f"No output: {message}"
        )
        self._append(f"ERROR: {message}")

    # -- widgets -------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.query_one("#run2d-start", Button).disabled = busy
        self.query_one("#run2d-cancel", Button).disabled = not busy

    def _set_output_buttons(self, enabled: bool) -> None:
        self.query_one("#run2d-results", Button).disabled = not enabled
        self.query_one("#run2d-plots", Button).disabled = not enabled

    def _set_loading(self, visible: bool) -> None:
        self.query_one("#run2d-loading", LoadingIndicator).display = visible

    def _status(self, message: str) -> None:
        self.query_one("#run2d-status", Static).update(message)
