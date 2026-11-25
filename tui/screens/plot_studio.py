"""Plot studio for scalar, angular, k-history and SCS plots."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, Input, Label, Select, Static

from ..services import export, plots, terminal
from ..services.paths import default_plot_path, resolve_path
from ..services.results import list_outputs
from ..widgets import ImagePreview


class PlotStudioPane(VerticalScroll):
    """Generate PNGs from one result file."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loaded = False
        self._pending_source: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Plot studio", classes="title")
        yield Horizontal(
            Select([], prompt="Select result file...", id="plot-result"),
            Button("Refresh", id="plot-refresh"),
            classes="button-row",
        )
        yield Horizontal(
            Label("Run", classes="field-label"),
            Select([], prompt="Select run...", id="plot-run"),
            classes="field-row",
        )
        yield Horizontal(
            Label("Kind", classes="field-label"),
            Select(
                [
                    ("Scalar flux", "scalar"),
                    ("Angular flux", "angular"),
                    ("k_eff history", "k-history"),
                ],
                value="scalar",
                allow_blank=False,
                id="plot-kind",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output PNG", classes="field-label"),
            Input(
                value=str(default_plot_path("scalar")),
                id="plot-output",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Button("Generate", id="plot-generate", variant="primary"),
            Button("Open", id="plot-open"),
            classes="button-row",
        )
        yield Static("", id="plot-status", classes="status")
        yield ImagePreview(id="plot-preview", classes="preview")

        yield Static("SCS / datos.json", classes="section-title")
        yield Horizontal(
            Label("Datos JSON", classes="field-label"),
            Input(value=str(export.default_datos_path()), id="scs-datos"),
            classes="field-row",
        )
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
                id="scs-x",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Output PNG", classes="field-label"),
            Input(
                value=str(default_plot_path("scs")),
                id="scs-output",
            ),
            classes="field-row",
        )
        yield Button("Generate SCS", id="scs-generate", variant="primary")
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        """Load results and apply a source requested before composition."""
        self.ensure_loaded()
        if self._pending_source is not None:
            target, self._pending_source = self._pending_source, None
            self._apply_source(target)

    def ensure_loaded(self) -> None:
        """Load result files only when the tab is opened."""
        if self._loaded:
            return
        self._loaded = True
        self.refresh_results()

    def refresh_results(self) -> None:
        self._loaded = True
        options = [(path.name, str(path)) for path in list_outputs()]
        select = self.query_one("#plot-result", Select)
        previous = None if select.is_blank() else str(select.value)
        select.set_options(options)
        if not options:
            return
        values = {value for _, value in options}
        select.value = previous if previous in values else options[-1][1]
        self.refresh_runs()

    def refresh_runs(self) -> None:
        select = self.query_one("#plot-result", Select)
        run_select = self.query_one("#plot-run", Select)
        if select.is_blank():
            run_select.set_options([])
            return
        try:
            options = plots.available_runs(Path(str(select.value)))
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Cannot read runs:[/] {exc}")
            run_select.set_options([])
            return
        run_select.set_options(options)
        if options:
            kind = self.query_one("#plot-kind", Select).value
            if kind == "angular" and len(options) > 1:
                run_select.value = options[1][1]
            else:
                run_select.value = options[0][1]

    def set_source(self, path: Path | str) -> None:
        """Select *path*, waiting for composition when necessary."""
        self._loaded = True
        self._pending_source = str(Path(path))
        try:
            self.query_one("#plot-result", Select)
        except NoMatches:
            return  # `_after_compose` will apply it
        target, self._pending_source = self._pending_source, None
        self._apply_source(target)

    def _apply_source(self, target: str) -> None:
        options = [(item.name, str(item)) for item in list_outputs()]
        if target not in {value for _, value in options}:
            if not Path(target).exists():
                self._status(f"Result not found: {target}")
                return
            options.append((Path(target).name, target))
        select = self.query_one("#plot-result", Select)
        select.set_options(options)
        select.value = target
        self.refresh_runs()
        self._status(f"Ready to plot {Path(target).name}.")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "plot-result":
            self.refresh_runs()
        elif event.select.id == "plot-kind":
            kind = str(event.select.value)
            if kind in {"scalar", "angular", "k-history"}:
                self.query_one("#plot-output", Input).value = str(
                    default_plot_path(kind)
                )
                self.refresh_runs()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "plot-refresh":
            self.refresh_results()
        elif button == "plot-generate":
            self._generate()
        elif button == "plot-open":
            output = Path(self.query_one("#plot-output", Input).value.strip())
            if output.exists():
                terminal.open_path(output)
        elif button == "scs-generate":
            self._generate_scs()

    def _run_selector(self) -> list[str] | None:
        select = self.query_one("#plot-run", Select)
        if select.is_blank():
            return None
        value = str(select.value)
        return ["all"] if value == "all" else [value]

    def _generate(self) -> None:
        result_select = self.query_one("#plot-result", Select)
        if result_select.is_blank():
            self._status("Select a result file first.")
            return
        kind = str(self.query_one("#plot-kind", Select).value)
        output_text = self.query_one("#plot-output", Input).value.strip()
        output = resolve_path(output_text) if output_text else default_plot_path(kind)
        try:
            produced = plots.generate(
                Path(str(result_select.value)),
                kind,
                output,
                run_selector=self._run_selector(),
            )
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Plot failed:[/] {exc}")
            return
        self.query_one("#plot-output", Input).value = str(produced)
        self.query_one("#plot-preview", ImagePreview).show(produced)
        self._status(f"Plot saved: {produced}")

    def _generate_scs(self) -> None:
        datos = resolve_path(self.query_one("#scs-datos", Input).value.strip())
        output = resolve_path(self.query_one("#scs-output", Input).value.strip())
        x_key = str(self.query_one("#scs-x", Select).value)
        try:
            produced = export.write_scs_plot(datos, output, x_key)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]SCS plot failed:[/] {exc}")
            return
        self.query_one("#scs-output", Input).value = str(produced)
        self.query_one("#plot-preview", ImagePreview).show(produced)
        self._status(f"SCS plot saved: {produced}")

    def _status(self, message: str) -> None:
        self.query_one("#plot-status", Static).update(message)
