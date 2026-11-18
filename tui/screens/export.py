"""Export datos.json, Excel workbooks and SCS plots."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, Select, Static

from ..services import export
from ..services.paths import resolve_path
from ..services.results import list_outputs


class ExportPane(VerticalScroll):
    """Data extraction and export actions."""

    def compose(self) -> ComposeResult:
        yield Static("Export", classes="title")
        yield Horizontal(
            Select([], prompt="Select result file...", id="export-file"),
            Button("Refresh", id="export-refresh"),
            classes="button-row",
        )

        yield Static("datos.json", classes="section-title")
        yield Horizontal(
            Label("Cell indices", classes="field-label"),
            Input(value="0, 20, 40, 50, 99", id="export-positions"),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output JSON", classes="field-label"),
            Input(
                value=str(export.default_datos_path()),
                id="export-datos",
            ),
            classes="field-row",
        )
        yield Button("Extract flux", id="export-extract", variant="primary")

        yield Static("Excel", classes="section-title")
        yield Horizontal(
            Label("Workbook", classes="field-label"),
            Input(placeholder="blank = next to the result JSON", id="export-excel"),
            classes="field-row",
        )
        yield Button("Write Excel", id="export-write-excel", variant="primary")

        yield Static("SCS plot", classes="section-title")
        yield Horizontal(
            Label("x axis", classes="field-label"),
            Select(
                [
                    ("SCS", "SCS"),
                    ("nu*Sigma_f", "NU_SIGF"),
                    ("k_eff", "k_eff"),
                ],
                value="SCS",
                allow_blank=False,
                id="export-x",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output PNG", classes="field-label"),
            Input(
                value="outputs/results/plots/scs_flux.png",
                id="export-plot",
            ),
            classes="field-row",
        )
        yield Button("Write SCS plot", id="export-scs", variant="primary")
        yield Static("", id="export-status", classes="status")
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self.refresh_outputs()

    def refresh_outputs(self) -> None:
        options = [(path.name, str(path)) for path in list_outputs()]
        select = self.query_one("#export-file", Select)
        select.set_options(options)
        if options:
            select.value = options[-1][1]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "export-refresh":
            self.refresh_outputs()
        elif button == "export-extract":
            self._extract()
        elif button == "export-write-excel":
            self._excel()
        elif button == "export-scs":
            self._scs()

    def _source(self) -> Path:
        select = self.query_one("#export-file", Select)
        if select.is_blank():
            raise ValueError("Select a result file first.")
        return Path(str(select.value))

    def _extract(self) -> None:
        try:
            source = self._source()
            positions = export.parse_positions(
                self.query_one("#export-positions", Input).value
            )
            text = self.query_one("#export-datos", Input).value.strip()
            output = resolve_path(text) if text else export.default_datos_path()
            produced = export.extract_positions(source, positions, output)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Extract failed:[/] {exc}")
            return
        self._status(f"datos.json written: {produced}")

    def _excel(self) -> None:
        try:
            source = self._source()
            text = self.query_one("#export-excel", Input).value.strip()
            produced = export.write_excel(source, resolve_path(text) if text else None)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Excel failed:[/] {exc}")
            return
        self.query_one("#export-excel", Input).value = str(produced)
        self._status(f"Excel written: {produced}")

    def _scs(self) -> None:
        try:
            datos = resolve_path(self.query_one("#export-datos", Input).value.strip())
            output = resolve_path(self.query_one("#export-plot", Input).value.strip())
            x_key = str(self.query_one("#export-x", Select).value)
            produced = export.write_scs_plot(datos, output, x_key)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]SCS plot failed:[/] {exc}")
            return
        self.query_one("#export-plot", Input).value = str(produced)
        self._status(f"SCS plot written: {produced}")

    def _status(self, message: str) -> None:
        self.query_one("#export-status", Static).update(message)
