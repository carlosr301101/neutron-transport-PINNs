"""Results browser for 2D solver output."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, DataTable, Select, Static

from ..services import results


class Results2DPane(VerticalScroll):
    """Table of 2D result files with MFLUX statistics."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._paths: list[Path] = []
        self._loaded = False
        self._suppress_selection = False

    def compose(self) -> ComposeResult:
        yield Static("2D results", classes="title")
        yield Horizontal(
            Select([], prompt="Select result file...", id="res2d-file"),
            Button("Refresh", id="res2d-refresh"),
            Button("Use in Plots", id="res2d-to-plots", variant="primary"),
            classes="button-row",
        )
        yield DataTable(id="res2d-table", cursor_type="row")
        yield Static("", id="res2d-detail", classes="detail")
        self.call_after_refresh(self.ensure_loaded)

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self.refresh_outputs()

    def refresh_outputs(self) -> None:
        self._loaded = True
        select = self.query_one("#res2d-file", Select)
        previous = None if select.is_blank() else str(select.value)
        suppress = self._suppress_selection
        self._suppress_selection = False

        options = [(path.name, str(path)) for path in results.list_outputs()]
        select.set_options(options)
        if options:
            values = {value for _, value in options}
            if suppress and previous in values:
                select.value = previous
            else:
                select.value = options[-1][1]
            self.refresh_table()
        else:
            self.query_one("#res2d-table", DataTable).clear(columns=True)
            self.query_one("#res2d-detail", Static).update(
                "No 2D output_*.json files yet. Run a configuration first."
            )

    def select_path(self, path: Path | str) -> None:
        """Select a specific result file, adding it if it lives elsewhere."""
        path = Path(path)
        options = [(item.name, str(item)) for item in results.list_outputs()]
        if str(path) not in {value for _, value in options}:
            if not path.is_file():
                return
            options.append((path.name, str(path)))
        select = self.query_one("#res2d-file", Select)
        self._suppress_selection = True
        select.set_options(options)
        select.value = str(path)
        self._loaded = True
        self.refresh_table()

    def refresh_table(self) -> None:
        select = self.query_one("#res2d-file", Select)
        table = self.query_one("#res2d-table", DataTable)
        table.clear(columns=True)
        if select.is_blank():
            return
        path = Path(str(select.value))
        try:
            summary = results.summarize(path)
        except Exception as exc:  # noqa: BLE001
            self.query_one("#res2d-detail", Static).update(
                f"[red]Load failed:[/] {exc}"
            )
            return

        table.add_columns("STATUS", "ITER", "CPU [s]", "Grid", "Mean flux")
        table.add_row(
            str(summary["status"]),
            "" if summary["iterations"] is None else str(summary["iterations"]),
            self._number(summary["cpu"], 6),
            f"{summary['rows']}x{summary['cols']}",
            self._number(summary["mean"], 4),
        )
        self._paths = [path]
        self.query_one("#res2d-detail", Static).update(
            f"{path.name}: select the row for details."
        )

    @staticmethod
    def _number(value, digits: int) -> str:
        if isinstance(value, (int, float)):
            return f"{value:.{digits}f}"
        return ""

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "res2d-file":
            self.refresh_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "res2d-refresh":
            self.refresh_outputs()
        elif event.button.id == "res2d-to-plots":
            select = self.query_one("#res2d-file", Select)
            if not select.is_blank() and hasattr(self.app, "set_plot_source"):
                self.app.set_plot_source(Path(str(select.value)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not self._paths:
            return
        path = self._paths[0]
        try:
            summary = results.summarize(path)
        except Exception as exc:  # noqa: BLE001
            self.query_one("#res2d-detail", Static).update(
                f"[red]Load failed:[/] {exc}"
            )
            return
        lines = [
            f"[b]File[/b]    {path}",
            f"[b]STATUS[/b]  {summary['status']}",
            f"[b]ITER[/b]    {summary['iterations']}",
            f"[b]CPU[/b]     {self._number(summary['cpu'], 8)} s",
            f"[b]Grid[/b]    {summary['rows']} x {summary['cols']} cells",
            f"[b]Mean[/b]    {self._number(summary['mean'], 6)}",
            f"[b]Min[/b]     {self._number(summary['min'], 6)}",
            f"[b]Max[/b]     {self._number(summary['max'], 6)}",
        ]
        self.query_one("#res2d-detail", Static).update("\n".join(lines))
