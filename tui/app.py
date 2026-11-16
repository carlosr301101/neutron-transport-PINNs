"""NTS 1D terminal user interface."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .log import configure_logging
from .screens.config_editor import ConfigEditorPane
from .screens.dashboard import DashboardPane
from .screens.export import ExportPane
from .screens.plot_studio import PlotStudioPane
from .screens.results import ResultsPane
from .screens.run_manager import RunManagerPane
from .screens.sweep import SweepPane

_TAB_PANES = {
    "tab-results": ResultsPane,
    "tab-plots": PlotStudioPane,
}


class NTSApp(App):
    """Main Textual application."""

    TITLE = "NTS Control"
    SUB_TITLE = "1D neutron transport"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardPane(classes="pane")
            with TabPane("Config", id="tab-config"):
                yield ConfigEditorPane(classes="pane")
            with TabPane("Run", id="tab-run"):
                yield RunManagerPane(classes="pane")
            with TabPane("Results", id="tab-results"):
                yield ResultsPane(classes="pane")
            with TabPane("Plots", id="tab-plots"):
                yield PlotStudioPane(classes="pane")
            with TabPane("Sweep", id="tab-sweep"):
                yield SweepPane(classes="pane")
            with TabPane("Export", id="tab-export"):
                yield ExportPane(classes="pane")
        yield Footer()

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Load data for a tab only when the user opens it."""
        pane_type = _TAB_PANES.get(event.pane.id)
        if pane_type is None:
            return
        pane = self.query_one(pane_type)
        ensure_loaded = getattr(pane, "ensure_loaded", None)
        if callable(ensure_loaded):
            ensure_loaded()

    def refresh_all(self) -> None:
        """Refresh every pane that shows filesystem data.

        ``refresh_results`` used to touch only the results table, which left
        the Plots/Export selectors and the dashboard counters stale.
        """
        refreshers = (
            (DashboardPane, "refresh_status"),
            (ConfigEditorPane, "refresh_load_options"),
            (RunManagerPane, "refresh_configs"),
            (ResultsPane, "refresh_outputs"),
            (PlotStudioPane, "refresh_results"),
            (SweepPane, "refresh_configs"),
            (ExportPane, "refresh_outputs"),
        )
        for pane_type, method_name in refreshers:
            try:
                pane = self.query_one(pane_type)
                getattr(pane, method_name)()
            except Exception:
                self.log.debug(
                    "refresh failed for %s.%s",
                    pane_type.__name__,
                    method_name,
                    exc_info=True,
                )

    def refresh_results(self) -> None:
        """Compatibility alias kept for callers from before ``refresh_all``."""
        self.refresh_all()

    def set_plot_source(self, path: Path | str) -> None:
        """Send a result file to the plot studio and switch tabs."""
        self.query_one(PlotStudioPane).set_source(path)
        self.query_one("#tabs", TabbedContent).active = "tab-plots"

    def on_unmount(self) -> None:
        """Stop any solver still running when the app closes."""
        for pane_type in (RunManagerPane, SweepPane):
            try:
                self.query_one(pane_type).cancel_run()
            except Exception:  # noqa: BLE001 - shutdown must not raise
                self.log.debug("cancel failed for %s", pane_type.__name__)


def main() -> None:
    configure_logging()
    NTSApp().run()


if __name__ == "__main__":
    main()
