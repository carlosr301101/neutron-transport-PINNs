"""Dashboard for the 2D TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from .. import __version__
from ..services import config_store, results


class Dashboard2DPane(VerticalScroll):
    """Version, file counts and the latest result."""

    def compose(self) -> ComposeResult:
        yield Static("NTS 2D", classes="title")
        yield Static("", id="dash2d-status", classes="status")
        yield Static(
            "Config: edit zones, regions and maps with a proportional domain "
            "view.\nRun: execute the C solvers. Results: MFLUX statistics. "
            "Plots: heatmaps in cm.",
            classes="muted",
        )

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        configs = config_store.list_configs()
        outputs = results.list_outputs()
        lines = [
            f"Version: {__version__}",
            f"Configurations: {len(configs)}",
            f"Results: {len(outputs)}",
        ]
        if outputs:
            latest = outputs[-1]
            try:
                summary = results.summarize(latest)
                lines.append(
                    f"Latest: {latest.name} · STATUS={summary['status']} · "
                    f"ITER={summary['iterations']} · "
                    f"{summary['rows']}x{summary['cols']} cells"
                )
            except Exception as exc:  # noqa: BLE001
                lines.append(f"Latest: {latest.name} (unreadable: {exc})")
        else:
            lines.append("Latest: no results yet")
        self.query_one("#dash2d-status", Static).update("\n".join(lines))
