"""NTS 1D terminal user interface."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .screens.config_editor import ConfigEditorPane
from .screens.dashboard import DashboardPane
from .screens.export import ExportPane
from .screens.plot_studio import PlotStudioPane
from .screens.results import ResultsPane
from .screens.run_manager import RunManagerPane
from .screens.sweep import SweepPane


class NTSApp(App):
    """Main Textual application."""

    TITLE = "NTS Control"
    SUB_TITLE = "1D neutron transport"
    CSS = """
    Screen {
        layout: vertical;
    }

    #tabs {
        height: 1fr;
    }

    TabPane {
        height: 1fr;
        padding: 1 2;
    }

    .pane {
        height: 1fr;
    }

    .title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        margin-bottom: 0;
    }

    .field-label {
        width: 34;
        padding-top: 1;
    }

    .field-row {
        height: auto;
        margin-bottom: 0;
    }

    .button-row {
        height: auto;
        margin: 1 0;
    }

    .button-row Button {
        margin-right: 1;
    }

    .status {
        margin: 1 0;
        text-style: italic;
    }

    .detail {
        border: round $primary;
        padding: 1;
        margin-top: 1;
    }

    .preview {
        height: 22;
        border: round $secondary;
        margin-top: 1;
    }

    .muted {
        color: $text-muted;
    }

    #run-configs {
        height: 9;
        border: round $primary;
    }

    #run-log {
        height: 12;
        border: round $primary;
    }

    #sweep-log {
        height: 12;
        border: round $primary;
    }

    #results-table {
        height: 14;
    }

    #sweep-ranges {
        height: auto;
    }
    """

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

    def refresh_results(self) -> None:
        """Refresh the results table after a run."""
        self.query_one(ResultsPane).refresh_outputs()

    def set_plot_source(self, path: Path | str) -> None:
        """Send a result file to the plot studio and switch tabs."""
        self.query_one(PlotStudioPane).set_source(path)
        self.query_one("#tabs", TabbedContent).active = "tab-plots"


def main() -> None:
    NTSApp().run()


if __name__ == "__main__":
    main()
