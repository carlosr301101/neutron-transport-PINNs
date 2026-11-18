"""Project dashboard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static

from tui import __version__

from ..services.config_store import list_configs
from ..services.results import list_outputs


class DashboardPane(VerticalScroll):
    """Overview of configs, results and next actions."""

    def compose(self) -> ComposeResult:
        yield Static("NTS Control", classes="title")
        yield Static(
            "Create a configuration, run it, then inspect results and plots.",
            classes="muted",
        )
        yield Static("", id="dash-status")
        yield Horizontal(
            Button("Refresh", id="dash-refresh", variant="primary"),
            classes="button-row",
        )
        yield Static(
            "Tabs: Config wizard, Run, Results, Plots, Placeholders, Export.",
            classes="muted",
        )

    def on_mount(self) -> None:
        self.refresh_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dash-refresh":
            self.refresh_status()

    def refresh_status(self) -> None:
        configs = list_configs()
        outputs = list_outputs()

        lines = [
            f"[b]Version[/b]  {__version__}",
            f"[b]Config files[/b]  {len(configs)}",
            f"[b]Result files[/b]  {len(outputs)}",
            "",
            "[b]Quick start[/b]",
            "1. Config wizard: fill geometry, materials, mode and source.",
            "2. Save the JSON under outputs/inputs/.",
            "3. Run: select one or more configs.",
            "4. Results: inspect k_eff, iterations and convergence.",
            "5. Plots: generate scalar, angular, k-history or SCS images.",
        ]
        self.query_one("#dash-status", Static).update("\n".join(lines))
