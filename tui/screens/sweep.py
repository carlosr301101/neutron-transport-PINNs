"""Placeholder sweep builder and batch runner."""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    LoadingIndicator,
    RichLog,
    Select,
    Static,
    Switch,
)

from core.placeholders import detect_placeholders

from ..services.config_store import list_configs, load_config
from ..services.paths import resolve_path
from ..services.results import next_result_path
from ..services.sweeps import expand_configs, save_configs
from ..widgets.run_panel import RunPanel


class SweepPane(RunPanel, VerticalScroll):
    """Expand placeholders and run the resulting configurations."""

    log_id = "sweep-log"
    status_id = "sweep-status"
    start_id = "sweep-run"
    cancel_id = "sweep-cancel"
    loading_id = "sweep-loading"
    failure_label = "Sweep failed"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config: dict = {}
        self._placeholders: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("Sweep builder", classes="title")
        yield Horizontal(
            Select([], prompt="Select config with placeholders...", id="sweep-file"),
            Button("Load", id="sweep-load"),
            Button("Preview", id="sweep-preview"),
            Button("Save", id="sweep-save", variant="primary"),
            classes="button-row",
        )
        yield Horizontal(
            Label("Output configs", classes="field-label"),
            Input(
                value="outputs/inputs/inputs_1d.json",
                id="sweep-output",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Excel", classes="field-label"),
            Switch(value=False, id="sweep-excel"),
            classes="field-row",
        )
        yield Horizontal(
            Button("Run sweep", id="sweep-run", variant="success"),
            Button("Cancel", id="sweep-cancel", variant="error"),
            LoadingIndicator(id="sweep-loading"),
            classes="button-row",
        )
        yield Static("Ranges", classes="section-title")
        yield Container(id="sweep-ranges")
        yield Static("", id="sweep-status", classes="status")
        yield RichLog(id="sweep-log", markup=False, wrap=True)

    def on_mount(self) -> None:
        self.init_run_panel()
        self.refresh_configs()

    def refresh_configs(self) -> None:
        options = [(path.name, str(path)) for path in list_configs()]
        select = self.query_one("#sweep-file", Select)
        select.set_options(options)
        if options:
            select.value = options[-1][1]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "sweep-load":
            self._load()
        elif button == "sweep-preview":
            self._preview()
        elif button == "sweep-save":
            self._save()
        elif button == "sweep-run":
            self._run()
        elif button == "sweep-cancel":
            self.cancel_run()

    def _load(self) -> None:
        select = self.query_one("#sweep-file", Select)
        if select.is_blank():
            self._set_status("Select a configuration first.")
            return
        try:
            self._config = load_config(Path(str(select.value)))
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Load failed:[/] {exc}")
            return

        self._placeholders = sorted(detect_placeholders(self._config))
        container = self.query_one("#sweep-ranges", Container)
        container.remove_children()
        if not self._placeholders:
            self._set_status("No placeholders in this configuration.")
            return

        for name in self._placeholders:
            container.mount(
                Horizontal(
                    Label(name, classes="field-label"),
                    Input(placeholder="start", id=f"sweep-start-{name}"),
                    Input(placeholder="end", id=f"sweep-end-{name}"),
                    Input(placeholder="step", id=f"sweep-step-{name}"),
                    classes="field-row",
                )
            )
        self._set_status("Placeholders: " + ", ".join(self._placeholders))

    def _ranges(self) -> dict[str, tuple[str, str, str]]:
        ranges: dict[str, tuple[str, str, str]] = {}
        for name in self._placeholders:
            start = self.query_one(f"#sweep-start-{name}", Input).value.strip()
            end = self.query_one(f"#sweep-end-{name}", Input).value.strip()
            step = self.query_one(f"#sweep-step-{name}", Input).value.strip()
            if not start or not end or not step:
                raise ValueError(f"Fill start, end and step for {name!r}.")
            ranges[name] = (start, end, step)
        return ranges

    def _expanded(self) -> list[dict]:
        if not self._placeholders:
            raise ValueError("Load a configuration with placeholders first.")
        return expand_configs(self._config, self._ranges())

    def _output_path(self) -> Path:
        text = self.query_one("#sweep-output", Input).value.strip()
        return resolve_path(text or "outputs/inputs/inputs_1d.json")

    def _preview(self) -> None:
        try:
            configs = self._expanded()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Preview failed:[/] {exc}")
            return
        self.query_one("#sweep-log", RichLog).write(
            f"{len(configs)} configuration(s). First:\n"
            + json.dumps(configs[0], indent=2)
        )
        self._set_status(f"{len(configs)} configuration(s) ready.")

    def _save(self) -> None:
        try:
            configs = self._expanded()
            saved = save_configs(configs, self._output_path())
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Save failed:[/] {exc}")
            return
        self._set_status(f"Saved {len(configs)} configurations: {saved}")

    def _run(self) -> None:
        try:
            configs = self._expanded()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Cannot run:[/] {exc}")
            return

        output_configs = self._output_path()
        try:
            saved = save_configs(configs, output_configs)
            if saved.suffix.lower() == ".json":
                run_path = saved
            else:
                run_path = save_configs(configs, saved.with_suffix(".json"))
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Cannot save sweep:[/] {exc}")
            return

        output = next_result_path()
        excel = self.query_one("#sweep-excel", Switch).value
        self.start_run(run_path, output, excel=excel)

    def on_run_complete(self, result: dict) -> None:
        code = result.get("returncode")
        output = result.get("output_path")
        if result.get("cancelled"):
            self._set_status(f"Sweep cancelled (code {code}). Partial output: {output}")
        else:
            self._set_status(f"Sweep finished (code {code}). Output: {output}")
        self.app.refresh_all()
