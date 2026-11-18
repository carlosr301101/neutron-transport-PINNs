"""NTS 1D terminal user interface."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .log import configure_logging
from .screens.config_editor import ConfigEditorPane
from .screens.dashboard import DashboardPane
from .screens.export import ExportPane
from .screens.placeholders import PlaceholdersPane
from .screens.plot_studio import PlotStudioPane
from .screens.results import ResultsPane
from .screens.run_manager import RunManagerPane

_TAB_PANES = {
    "tab-config": ConfigEditorPane,
    "tab-run": RunManagerPane,
    "tab-results": ResultsPane,
    "tab-plots": PlotStudioPane,
    "tab-placeholders": PlaceholdersPane,
    "tab-export": ExportPane,
}


class NTSApp(App):
    """Main Textual application."""

    TITLE = "NTS Control"
    SUB_TITLE = "1D neutron transport"
    CSS_PATH = "app.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pane_mount_locks: dict[str, asyncio.Lock] = {}
        self._pending_plot_source: str | None = None

    def _pane_lock(self, tab_id: str) -> asyncio.Lock:
        lock = self._pane_mount_locks.get(tab_id)
        if lock is None:
            lock = asyncio.Lock()
            self._pane_mount_locks[tab_id] = lock
        return lock

    def on_mount(self) -> None:
        # Build the most-used tab after the dashboard is visible.  The mount
        # lock in _ensure_pane makes this safe if the user clicks Config first.
        self.call_after_refresh(self._start_preload)

    def _start_preload(self) -> None:
        self.run_worker(self._preload_config(), group="preload", exclusive=False)

    async def _preload_config(self) -> None:
        try:
            await self._ensure_pane("tab-config")
        except Exception:
            self.log.debug("config preload failed", exc_info=True)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardPane(classes="pane")
            with TabPane("Config", id="tab-config"):
                pass
            with TabPane("Run", id="tab-run"):
                pass
            with TabPane("Results", id="tab-results"):
                pass
            with TabPane("Plots", id="tab-plots"):
                pass
            with TabPane("Placeholders", id="tab-placeholders"):
                pass
            with TabPane("Export", id="tab-export"):
                pass
        yield Footer()

    async def _ensure_pane(self, tab_id: str):
        """Mount the pane for *tab_id* on first use and return it."""
        pane_type = _TAB_PANES[tab_id]
        async with self._pane_lock(tab_id):
            tab = self.query_one(f"#{tab_id}", TabPane)
            if not tab.children:
                pane = pane_type(classes="pane")
                await tab.mount(pane)
                return pane
            return tab.children[0]

    async def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Mount the pane for a tab the first time it is opened.

        Cada panel programa su propia carga desde ``compose`` con
        ``call_after_refresh``: así los hijos ya existen cuando se consultan.
        """
        tab_id = event.pane.id
        if tab_id not in _TAB_PANES:
            return
        await self._ensure_pane(tab_id)
        if tab_id == "tab-plots":
            self._apply_pending_plot_source()

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
            (PlaceholdersPane, "refresh_configs"),
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
        """Send a result file to the plot studio and switch tabs.

        Primero monta el panel y después activa la pestaña: Textual revierte
        la activación si el ``TabPane`` todavía está vacío.  La carga del
        archivo se aplica cuando el panel está compuesto (o de inmediato si
        ya lo estaba).
        """
        self._pending_plot_source = str(path)
        self.call_next(self._show_plots)

    async def _show_plots(self) -> None:
        pane = await self._ensure_pane("tab-plots")
        self.query_one("#tabs", TabbedContent).active = "tab-plots"
        # Mover el foco al panel evita que TabbedContent reactive la pestaña
        # anterior al recibir el DescendantFocus del botón que se acaba de usar.
        self.set_focus(pane)
        self._apply_pending_plot_source()

    def _apply_pending_plot_source(self) -> None:
        path = self._pending_plot_source
        self._pending_plot_source = None
        if not path:
            return
        try:
            self.query_one(PlotStudioPane).set_source(path)
        except Exception:
            self.log.debug("plot source failed", exc_info=True)

    def on_unmount(self) -> None:
        """Stop any solver still running when the app closes."""
        for pane_type in (RunManagerPane, PlaceholdersPane):
            try:
                self.query_one(pane_type).cancel_run()
            except Exception:  # noqa: BLE001 - shutdown must not raise
                self.log.debug("cancel failed for %s", pane_type.__name__)


def main() -> None:
    configure_logging()
    NTSApp().run()


if __name__ == "__main__":
    main()
