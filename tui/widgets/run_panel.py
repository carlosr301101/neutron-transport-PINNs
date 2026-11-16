"""Subprocess plumbing shared by the Run and Sweep tabs.

Both panes stream ``cli.run_1d`` into a ``RichLog`` and need the same
start/cancel/loading handling, so it lives here instead of being duplicated.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual import work
from textual.css.query import NoMatches
from textual.widgets import Button, LoadingIndicator, RichLog, Static

from ..services.runner import RunProcess


class RunPanel:
    """Mixin that adds a cancellable solver run to a Textual pane.

    The pane provides ``log_id``/``status_id``/``start_id``/``cancel_id``/
    ``loading_id`` widgets and overrides :meth:`on_run_complete` to react to
    the result.
    """

    log_id: ClassVar[str] = "run-log"
    status_id: ClassVar[str] = "run-status"
    start_id: ClassVar[str] = "run-start"
    cancel_id: ClassVar[str] = "run-cancel"
    loading_id: ClassVar[str] = "run-loading"
    failure_label: ClassVar[str] = "Run failed"

    def init_run_panel(self) -> None:
        """Reset the panel state; call from ``on_mount``."""
        self._process: RunProcess | None = None
        self._shutting_down = False
        self._set_loading(False)
        self._set_busy(False)

    @property
    def is_running(self) -> bool:
        process = getattr(self, "_process", None)
        return process is not None and process.is_running

    # -- actions -------------------------------------------------------
    def start_run(
        self,
        config_paths: list[Path] | Path,
        output: Path,
        *,
        scheme: str | None = None,
        excel: bool = False,
    ) -> None:
        """Launch the solver and stream its output into the log widget."""
        if getattr(self, "_shutting_down", False):
            return
        if self.is_running:
            self._set_status("A run is already in progress.")
            return

        self.query_one(f"#{self.log_id}", RichLog).clear()
        self._set_status("Running...")
        self._set_loading(True)
        self._set_busy(True)
        self._process = RunProcess()
        self._run_worker(config_paths, output, scheme, excel)

    def cancel_run(self) -> None:
        """Ask the running solver to stop."""
        process = getattr(self, "_process", None)
        if process is not None and process.is_running:
            process.cancel()
            self._set_status("Cancel requested.")

    def on_unmount(self) -> None:
        """Never leave a solver running after the app closes."""
        self._shutting_down = True
        process = getattr(self, "_process", None)
        if process is not None:
            process.cancel()
        self._process = None

    # -- worker --------------------------------------------------------
    @work(thread=True, exclusive=True)
    def _run_worker(
        self,
        config_paths: list[Path] | Path,
        output: Path,
        scheme: str | None,
        excel: bool,
    ) -> None:
        process = self._process
        if process is None:
            return

        def on_line(line: str) -> None:
            self._post(self._append, line)

        try:
            result = process.run(
                config_paths,
                output,
                excel=excel,
                scheme=scheme,
                on_line=on_line,
            )
        except Exception as exc:  # noqa: BLE001 - shown in the status line
            self._post(self._failed, str(exc))
            return
        self._post(self._finish, result)

    # -- main-thread updates ------------------------------------------
    def _post(self, callback, *args) -> None:
        """Hop back to the UI thread unless the app is shutting down."""
        if getattr(self, "_shutting_down", False):
            return
        try:
            self.app.call_from_thread(callback, *args)
        except RuntimeError:
            self._shutting_down = True

    def _append(self, line: str) -> None:
        if not self.is_mounted:
            return
        self.query_one(f"#{self.log_id}", RichLog).write(line)

    def _finish(self, result: dict) -> None:
        if getattr(self, "_shutting_down", False) or not self.is_mounted:
            return
        self._reset_controls()
        self.on_run_complete(result)

    def _failed(self, message: str) -> None:
        if getattr(self, "_shutting_down", False) or not self.is_mounted:
            return
        self._reset_controls()
        self._append(f"ERROR: {message}")
        self._set_status(f"[red]{self.failure_label}:[/] {message}")

    def on_run_complete(self, result: dict) -> None:
        """Hook for subclasses; called after the worker returns."""

    # -- widgets -------------------------------------------------------
    def _reset_controls(self) -> None:
        self._set_loading(False)
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        try:
            self.query_one(f"#{self.start_id}", Button).disabled = busy
            self.query_one(f"#{self.cancel_id}", Button).disabled = not busy
        except NoMatches:
            self.log.debug("run buttons are not mounted yet")

    def _set_loading(self, visible: bool) -> None:
        try:
            self.query_one(f"#{self.loading_id}", LoadingIndicator).display = visible
        except NoMatches:
            self.log.debug("loading indicator is not mounted yet")

    def _set_status(self, message: str) -> None:
        try:
            self.query_one(f"#{self.status_id}", Static).update(message)
        except NoMatches:
            self.log.debug("status widget is not mounted yet")
