"""Run manager for the 2D C solvers."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Label,
    LoadingIndicator,
    RichLog,
    Select,
    SelectionList,
    Static,
)

from ..models import DEFAULT_SOLVER, SOLVER_NAMES, build_preview
from ..services import config_store
from ..services.runner import SolverRunner


class Run2DPane(VerticalScroll):
    """Select configurations and run a 2D solver in subprocesses."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._runner: SolverRunner | None = None
        self._shutting_down = False

    def compose(self) -> ComposeResult:
        yield Static("2D run manager", classes="title")
        yield Horizontal(
            Button("Refresh", id="run2d-refresh"),
            Button("Run selected", id="run2d-start", variant="primary"),
            Button("Cancel", id="run2d-cancel", variant="error"),
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
        yield Static("", id="run2d-status", classes="status")
        yield Static("", id="run2d-preview", classes="preview-text", markup=False)
        yield RichLog(id="run2d-log", markup=False, wrap=True)
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self._set_loading(False)
        self._set_busy(False)
        self.refresh_configs()

    # -- state ---------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self._runner is not None

    def refresh_configs(self) -> None:
        selection = self.query_one("#run2d-configs", SelectionList)
        selection.clear_options()
        for path in config_store.list_configs():
            selection.add_option((path.name, str(path)))

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        self._update_preview()

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
            self.refresh_configs()
        elif button == "run2d-start":
            self._start()
        elif button == "run2d-cancel":
            self.cancel_run()

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
        self.query_one("#run2d-log", RichLog).clear()
        self._status("Running...")
        self._set_loading(True)
        self._set_busy(True)
        self._runner = SolverRunner()
        self._run_worker(paths, solver, workers)

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
    def _run_worker(self, paths: list[Path], solver: str, workers: int) -> None:
        runner = self._runner
        if runner is None:
            return

        def on_event(line: str) -> None:
            self._post(self._append, line)

        try:
            outcomes = runner.run(paths, solver, workers, on_event)
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
        self._append(self._status_text(outcomes))
        if hasattr(self.app, "refresh_all"):
            self.app.refresh_all()

    @staticmethod
    def _status_text(outcomes) -> str:
        lines = []
        for outcome in outcomes:
            if outcome.ok:
                lines.append(
                    f"OK {outcome.config.name}: STATUS={outcome.status} "
                    f"ITER={outcome.iterations} CPU={outcome.cpu}"
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
        self._status(f"[red]Run failed:[/] {message}")
        self._append(f"ERROR: {message}")

    # -- widgets -------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.query_one("#run2d-start", Button).disabled = busy
        self.query_one("#run2d-cancel", Button).disabled = not busy

    def _set_loading(self, visible: bool) -> None:
        self.query_one("#run2d-loading", LoadingIndicator).display = visible

    def _status(self, message: str) -> None:
        self.query_one("#run2d-status", Static).update(message)
