"""Placeholder range builder and batch runner."""

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

from core.placeholders import build_placeholder_values, detect_placeholders

from ..services.config_store import list_configs, load_config
from ..services.paths import resolve_path
from ..services.results import next_result_path
from ..services.sweeps import expand_configs, parse_range, save_configs
from ..widgets.run_panel import RunPanel

RANGE_HINT = (
    "Format: name [start:end:step]  ·  example: MM [10:20:1] generates "
    "10, 11, …, 20."
)


class PlaceholdersPane(RunPanel, VerticalScroll):
    """Expand placeholders over a range and run the resulting configs."""

    log_id = "ph-log"
    status_id = "ph-status"
    start_id = "ph-run"
    cancel_id = "ph-cancel"
    loading_id = "ph-loading"
    failure_label = "Batch failed"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config: dict = {}
        self._placeholders: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("Placeholder ranges", classes="title")
        yield Static(RANGE_HINT, classes="muted")
        yield Horizontal(
            Select([], prompt="Select config with placeholders...", id="ph-file"),
            Button("Refresh", id="ph-refresh"),
            Button("Load", id="ph-load"),
            Button("Preview", id="ph-preview"),
            Button("Save", id="ph-save", variant="primary"),
            classes="button-row",
        )
        yield Horizontal(
            Label("Output configs", classes="field-label"),
            Input(
                value="outputs/inputs/inputs_1d.json",
                id="ph-output",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Excel", classes="field-label"),
            Switch(value=False, id="ph-excel"),
            classes="field-row",
        )
        yield Horizontal(
            Button("Run batch", id="ph-run", variant="success"),
            Button("Cancel", id="ph-cancel", variant="error"),
            LoadingIndicator(id="ph-loading"),
            classes="button-row",
        )
        yield Static("Ranges", classes="section-title")
        yield Container(id="ph-ranges")
        yield Static("", id="ph-status", classes="status")
        yield RichLog(id="ph-log", markup=False, wrap=True)
        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self.init_run_panel()
        self.refresh_configs()

    def refresh_configs(self) -> None:
        options = [(path.name, str(path)) for path in list_configs()]
        select = self.query_one("#ph-file", Select)
        select.set_options(options)
        if options:
            select.value = options[-1][1]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "ph-refresh":
            self.refresh_configs()
        elif button == "ph-load":
            self._load()
        elif button == "ph-preview":
            self._preview()
        elif button == "ph-save":
            self._save()
        elif button == "ph-run":
            self._run()
        elif button == "ph-cancel":
            self.cancel_run()

    def _load(self) -> None:
        select = self.query_one("#ph-file", Select)
        if select.is_blank():
            self._set_status("Select a configuration first.")
            return
        try:
            self._config = load_config(Path(str(select.value)))
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Load failed:[/] {exc}")
            return

        self._placeholders = sorted(detect_placeholders(self._config))
        container = self.query_one("#ph-ranges", Container)
        container.remove_children()
        if not self._placeholders:
            self._set_status("No placeholders in this configuration.")
            return

        for name in self._placeholders:
            container.mount(
                Horizontal(
                    Label(name, classes="field-label"),
                    Input(placeholder="10:20:1", id=f"ph-range-{name}"),
                    classes="field-row",
                )
            )
        self._set_status(
            f"{len(self._placeholders)} placeholder(s): "
            + ", ".join(self._placeholders)
            + ". Fill a range like 10:20:1."
        )

    def _range_texts(self) -> dict[str, str]:
        texts: dict[str, str] = {}
        for name in self._placeholders:
            text = self.query_one(f"#ph-range-{name}", Input).value.strip()
            if not text:
                raise ValueError(f"Set a range for {name!r}, e.g. 10:20:1.")
            texts[name] = text
        return texts

    def _ranges(self) -> dict[str, tuple[str, str, str]]:
        return {name: parse_range(text) for name, text in self._range_texts().items()}

    @staticmethod
    def _describe(ranges: dict[str, tuple[str, str, str]]) -> str:
        lines = []
        for name, (start, end, step) in ranges.items():
            count = len(
                build_placeholder_values(float(start), float(end), float(step))
            )
            lines.append(
                f"{name}: {start} -> {end} (step {step}) = {count} value(s)"
            )
        return "\n".join(lines)

    def _expanded(self) -> list[dict]:
        if not self._placeholders:
            raise ValueError("Load a configuration with placeholders first.")
        return expand_configs(self._config, self._ranges())

    def _output_path(self) -> Path:
        text = self.query_one("#ph-output", Input).value.strip()
        return resolve_path(text or "outputs/inputs/inputs_1d.json")

    def _preview(self) -> None:
        try:
            ranges = self._ranges()
            configs = expand_configs(self._config, ranges) if self._placeholders else []
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"[red]Preview failed:[/] {exc}")
            return
        if not configs:
            self._set_status("Load a configuration with placeholders first.")
            return
        self.query_one("#ph-log", RichLog).write(
            self._describe(ranges)
            + f"\n\n{len(configs)} configuration(s). First:\n"
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
            self._set_status(f"[red]Cannot save batch:[/] {exc}")
            return

        output = next_result_path()
        excel = self.query_one("#ph-excel", Switch).value
        self.start_run(run_path, output, excel=excel)

    def on_run_complete(self, result: dict) -> None:
        code = result.get("returncode")
        output = result.get("output_path")
        if result.get("cancelled"):
            self._set_status(f"Batch cancelled (code {code}). Partial output: {output}")
        else:
            self._set_status(f"Batch finished (code {code}). Output: {output}")
        self.app.refresh_all()
