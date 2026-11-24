"""Heatmap studio for 2D results."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, Input, Label, Select, Static

from tui.services.paths import resolve_path
from tui.services.terminal import open_path

from ..services import plots, results
from ..widgets import ImagePreview


class Plots2DPane(VerticalScroll):
    """Generate and preview the ``MFLUX`` heatmap of one result."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loaded = False
        self._pending_source: str | None = None
        self._generating = False

    def compose(self) -> ComposeResult:
        yield Static("2D heatmaps", classes="title")
        yield Horizontal(
            Select([], prompt="Select result file...", id="plot2d-result"),
            Button("Refresh", id="plot2d-refresh"),
            classes="button-row",
        )
        yield Horizontal(
            Label("Input geometry", classes="field-label"),
            Input(
                value="",
                placeholder="auto: input_NNN.txt next to the result",
                id="plot2d-input",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output PNG", classes="field-label"),
            Input(value=str(plots.default_plot_path()), id="plot2d-output"),
            classes="field-row",
        )
        yield Horizontal(
            Button("Generate", id="plot2d-generate", variant="primary"),
            Button("Open", id="plot2d-open"),
            classes="button-row",
        )
        yield Static("", id="plot2d-status", classes="status")
        yield ImagePreview(id="plot2d-preview", classes="preview")
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self.ensure_loaded()
        if self._pending_source is not None:
            target, self._pending_source = self._pending_source, None
            self._apply_source(target)

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self.refresh_results()

    def refresh_results(self) -> None:
        self._loaded = True
        options = [(path.name, str(path)) for path in results.list_outputs()]
        select = self.query_one("#plot2d-result", Select)
        previous = None if select.is_blank() else str(select.value)
        select.set_options(options)
        if not options:
            return
        values = {value for _, value in options}
        select.value = previous if previous in values else options[-1][1]
        self._suggest_input()

    def _suggest_input(self) -> None:
        select = self.query_one("#plot2d-result", Select)
        if select.is_blank():
            return
        found = results.find_input_for_result(Path(str(select.value)))
        field = self.query_one("#plot2d-input", Input)
        if found is not None:
            field.value = str(found)

    def set_source(self, path: Path | str) -> None:
        """Select *path* (used by "Use in Plots")."""
        self._loaded = True
        self._pending_source = str(Path(path))
        try:
            self.query_one("#plot2d-result", Select)
        except NoMatches:
            return
        target, self._pending_source = self._pending_source, None
        self._apply_source(target)

    def _apply_source(self, target: str) -> None:
        options = [(path.name, str(path)) for path in results.list_outputs()]
        if target not in {value for _, value in options}:
            if not Path(target).exists():
                self._status(f"Result not found: {target}")
                return
            options.append((Path(target).name, target))
        select = self.query_one("#plot2d-result", Select)
        select.set_options(options)
        select.value = target
        self._suggest_input()
        self._status(f"Ready to plot {Path(target).name}.")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "plot2d-result":
            self._suggest_input()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "plot2d-refresh":
            self.refresh_results()
        elif button == "plot2d-generate":
            self._generate()
        elif button == "plot2d-open":
            output = Path(self.query_one("#plot2d-output", Input).value.strip())
            if output.exists():
                open_path(output)

    def _generate(self) -> None:
        if self._generating:
            return
        select = self.query_one("#plot2d-result", Select)
        if select.is_blank():
            self._status("Select a result file first.")
            return
        result_path = Path(str(select.value))
        input_text = self.query_one("#plot2d-input", Input).value.strip()
        input_path = resolve_path(input_text) if input_text else None
        output_text = self.query_one("#plot2d-output", Input).value.strip()
        output = (
            resolve_path(output_text) if output_text else plots.default_plot_path()
        )
        self._generating = True
        self._status("Generating heatmap...")
        self._generate_worker(result_path, output, input_path)

    @work(thread=True, exclusive=True)
    def _generate_worker(
        self, result_path: Path, output: Path, input_path: Path | None
    ) -> None:
        try:
            produced = plots.generate_heatmap(result_path, output, input_path)
        except Exception as exc:  # noqa: BLE001 - shown in the status line
            self.app.call_from_thread(self._failed, str(exc))
            return
        self.app.call_from_thread(self._done, produced)

    def _done(self, produced: Path) -> None:
        self._generating = False
        if not self.is_mounted:
            return
        self.query_one("#plot2d-output", Input).value = str(produced)
        self.query_one("#plot2d-preview", ImagePreview).show(produced)
        self._status(f"Plot saved: {produced}")

    def _failed(self, message: str) -> None:
        self._generating = False
        if not self.is_mounted:
            return
        self._status(f"[red]Plot failed:[/] {message}")

    def _status(self, message: str) -> None:
        self.query_one("#plot2d-status", Static).update(message)
