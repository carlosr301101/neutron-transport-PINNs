"""Results browser."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, DataTable, Select, Static

from ..services.results import (
    list_outputs,
    load_payload,
    summarize,
)


class ResultsPane(VerticalScroll):
    """Table of runs with a detail pane."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._payload: dict = {}
        self._row_index: dict[int, int] = {}
        self._loaded = False

    def compose(self) -> ComposeResult:
        yield Static("Results", classes="title")
        yield Horizontal(
            Select([], prompt="Select result file...", id="results-file"),
            Button("Refresh", id="results-refresh"),
            Button("Use in Plots", id="results-to-plots", variant="primary"),
            classes="button-row",
        )
        yield DataTable(id="results-table", cursor_type="row")
        yield Static("", id="results-detail", classes="detail")

    def ensure_loaded(self) -> None:
        """Load the latest result only when the tab is opened."""
        if self._loaded:
            return
        self._loaded = True
        self.refresh_outputs()

    def refresh_outputs(self) -> None:
        self._loaded = True
        options = [(path.name, str(path)) for path in list_outputs()]
        select = self.query_one("#results-file", Select)
        select.set_options(options)
        if options:
            select.value = options[-1][1]
            self.refresh_table()
        else:
            self.query_one("#results-table", DataTable).clear(columns=True)
            self.query_one("#results-detail", Static).update(
                "No output_1d_*.json files yet."
            )

    def refresh_table(self) -> None:
        select = self.query_one("#results-file", Select)
        if select.is_blank():
            return
        path = Path(str(select.value))
        try:
            self._payload = load_payload(path)
        except Exception as exc:  # noqa: BLE001
            self.query_one("#results-detail", Static).update(
                f"[red]Load failed:[/] {exc}"
            )
            return

        rows = summarize(self._payload)
        table = self.query_one("#results-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Run",
            "Mode",
            "Scheme",
            "k_eff",
            "k_balance",
            "Outer",
            "Flux updates",
            "Converged",
        )
        self._row_index = {}
        for table_row, row in enumerate(rows):
            self._row_index[table_row] = row["index"]
            table.add_row(
                row["name"],
                row["mode"],
                row["scheme"],
                self._number(row["k_eff"], 8),
                self._number(row["k_balance"], 8),
                "" if row["outer"] is None else str(row["outer"]),
                str(row["flux_updates"]),
                "yes" if row["converged"] else "no",
            )
        self.query_one("#results-detail", Static).update(
            f"{path.name}: {len(rows)} run(s). Select a row for details."
        )

    @staticmethod
    def _number(value, digits: int) -> str:
        if isinstance(value, (int, float)):
            return f"{value:.{digits}f}"
        return ""

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "results-file":
            self.refresh_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "results-refresh":
            self.refresh_outputs()
        elif event.button.id == "results-to-plots":
            select = self.query_one("#results-file", Select)
            if not select.is_blank():
                self.app.set_plot_source(Path(str(select.value)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        runs = self._payload.get("runs", [])
        index = self._row_index.get(event.cursor_row)
        if index is None or not 0 <= index < len(runs):
            return
        run = runs[index]
        if not isinstance(run, dict):  # summarize() already skips these
            return
        lines = [
            f"[b]Run[/b]      {run.get('config_name')}",
            f"[b]Mode[/b]     {run.get('mode')}",
            f"[b]Scheme[/b]   {run.get('spatial_scheme')}",
            f"[b]k_eff[/b]    {self._number(run.get('k_eff'), 10)}",
            f"[b]k_balance[/b]{self._number(run.get('k_balance'), 10)}",
            f"[b]Outer[/b]    {run.get('iteration_eigenvalue')}",
            f"[b]Flux upd[/b] {run.get('iteration')}",
            f"[b]Converged[/b] {run.get('converged')}",
        ]
        if run.get("error"):
            lines.append(f"[red]Error:[/] {run['error']}")
        scalar = run.get("scalar_flux") or []
        if scalar:
            lines.append("")
            lines.append(f"[b]Cells[/b]    {len(scalar)}")
            lines.append(f"[b]phi min[/b]  {min(scalar):.6g}")
            lines.append(f"[b]phi max[/b]  {max(scalar):.6g}")
        self.query_one("#results-detail", Static).update("\n".join(lines))
