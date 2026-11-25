"""NTS 2D terminal user interface."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .log import configure_logging
from .screens import (
    Config2DPane,
    Dashboard2DPane,
    Plots2DPane,
    Results2DPane,
    Run2DPane,
)

_TABS: dict[str, type] = {
    "tab2d-dashboard": Dashboard2DPane,
    "tab2d-config": Config2DPane,
    "tab2d-run": Run2DPane,
    "tab2d-results": Results2DPane,
    "tab2d-plots": Plots2DPane,
}

# Refreshed every time the tab is activated: the selectors must see files
# created by another pane, the CLI or another session.
_TAB_REFRESH: dict[str, tuple[type, str]] = {
    "tab2d-dashboard": (Dashboard2DPane, "refresh_status"),
    "tab2d-config": (Config2DPane, "refresh_load_options"),
    "tab2d-run": (Run2DPane, "refresh_files"),
    "tab2d-results": (Results2DPane, "refresh_outputs"),
    "tab2d-plots": (Plots2DPane, "refresh_results"),
}


class NTS2DApp(App):
    """Textual application for the 2D workflow."""

    TITLE = "NTS Control"
    SUB_TITLE = "2D neutron transport"
    CSS_PATH = "app.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Dashboard", id="tab2d-dashboard"):
                yield Dashboard2DPane(classes="pane")
            with TabPane("Config", id="tab2d-config"):
                yield Config2DPane(classes="pane")
            with TabPane("Run", id="tab2d-run"):
                yield Run2DPane(classes="pane")
            with TabPane("Results", id="tab2d-results"):
                yield Results2DPane(classes="pane")
            with TabPane("Plots", id="tab2d-plots"):
                yield Plots2DPane(classes="pane")
        yield Footer()

    def refresh_all(self) -> None:
        """Refresh every pane that shows filesystem data."""
        refreshers = (
            (Dashboard2DPane, "refresh_status"),
            (Config2DPane, "refresh_load_options"),
            (Run2DPane, "refresh_configs"),
            (Results2DPane, "refresh_outputs"),
            (Plots2DPane, "refresh_results"),
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

    def set_plot_source(self, path: Path | str) -> None:
        """Send a result file to the heatmap studio and switch tabs.

        The pane is selected *before* activating the tab so the activation
        refresh cannot replace the requested file with the newest one.
        """
        try:
            pane = self.query_one(Plots2DPane)
            pane.set_source(path)
            self.query_one("#tabs", TabbedContent).active = "tab2d-plots"
            self.set_focus(pane)
        except Exception:
            self.log.debug("plot source failed", exc_info=True)

    def show_results(self, path: Path | str | None = None) -> None:
        """Open the Results tab, optionally selecting one result file."""
        try:
            pane = self.query_one(Results2DPane)
            if path is not None:
                pane.select_path(path)
            self.query_one("#tabs", TabbedContent).active = "tab2d-results"
            self.set_focus(pane)
        except Exception:
            self.log.debug("show results failed", exc_info=True)

    async def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Refresh filesystem-backed panes when their tab is opened."""
        target = _TAB_REFRESH.get(event.pane.id)
        if target is None:
            return
        pane_type, method_name = target
        try:
            getattr(self.query_one(pane_type), method_name)()
        except Exception:
            self.log.debug(
                "tab refresh failed for %s", event.pane.id, exc_info=True
            )

    def on_unmount(self) -> None:
        try:
            self.query_one(Run2DPane).cancel_run()
        except Exception:
            self.log.debug("cancel failed", exc_info=True)


def main() -> None:
    configure_logging()
    NTS2DApp().run()


if __name__ == "__main__":
    main()
