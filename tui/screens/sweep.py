"""Placeholder sweep builder and batch runner."""

from __future__ import annotations

import json
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    Switch,
)

from core.placeholders import detect_placeholders

from ..services.config_store import list_configs, load_config
from ..services.results import next_result_path
from ..services.runner import RunProcess
from ..services.sweeps import expand_configs, save_configs


class SweepPane(VerticalScroll):
    """Expand placeholders and run the resulting configurations."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config: dict = {}
        self._placeholders: list[str] = []
        self._process: RunProcess | None = None

    def compose(self) -> ComposeResult:
        yield Static("Sweep builder", classes="title")
        yield Horizontal(
            Select([], prompt="Select config with placeholders...", id="sweep-file"),
            Button("Load", id="sweep-load"),
            Button("Preview", id="sweep-preview"),
            Button("Save", id="sweep-save", variant="primary"),
            Button("Run", id="sweep-run", variant="success"),
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
        yield Static("Ranges", classes="section-title")
        yield Container(id="sweep-ranges")
        yield Static("", id="sweep-status", classes="status")
        yield RichLog(id="sweep-log", markup=False, wrap=True)

    def on_mount(self) -> None:
        self.refresh_configs()

    def refresh_configs(self) -> None:
        options = [(path.name, str(path)) for path in list_configs()]
        self.query_one("#sweep-file", Select).set_options(options)
        if options:
            self.query_one("#sweep-file", Select).value = options[-1][1]

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

    def _load(self) -> None:
        select = self.query_one("#sweep-file", Select)
        if select.is_blank():
            self._status("Select a configuration first.")
            return
        try:
            self._config = load_config(Path(str(select.value)))
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Load failed:[/] {exc}")
            return

        self._placeholders = sorted(detect_placeholders(self._config))
        container = self.query_one("#sweep-ranges", Container)
        container.remove_children()
        if not self._placeholders:
            self._status("No placeholders in this configuration.")
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
        self._status("Placeholders: " + ", ".join(self._placeholders))

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
        return Path(text) if text else Path("outputs/inputs/inputs_1d.json")

    def _preview(self) -> None:
        try:
            configs = self._expanded()
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Preview failed:[/] {exc}")
            return
        self.query_one("#sweep-log", RichLog).write(
            f"{len(configs)} configuration(s). First:\n"
            + json.dumps(configs[0], indent=2)
        )
        self._status(f"{len(configs)} configuration(s) ready.")

    def _save(self) -> None:
        try:
            configs = self._expanded()
            saved = save_configs(configs, self._output_path())
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Save failed:[/] {exc}")
            return
        self._status(f"Saved {len(configs)} configurations: {saved}")

    def _run(self) -> None:
        try:
            configs = self._expanded()
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Cannot run:[/] {exc}")
            return

        try:
            saved = save_configs(configs, self._output_path())
            run_path = (
                saved
                if saved.suffix.lower() == ".json"
                else save_configs(configs, saved.with_suffix(".json"))
            )
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Cannot save sweep:[/] {exc}")
            return

        output = next_result_path()
        excel = self.query_one("#sweep-excel", Switch).value
        self.query_one("#sweep-log", RichLog).clear()
        self.query_one("#sweep-status", Static).update("Running sweep...")
        self._process = RunProcess()
        self._run_worker(run_path, output, excel)

    @work(thread=True, exclusive=True)
    def _run_worker(self, config_path: Path, output: Path, excel: bool) -> None:
        assert self._process is not None

        def on_line(line: str) -> None:
            self.app.call_from_thread(self._append, line)

        try:
            result = self._process.run(
                config_path,
                output,
                excel=excel,
                on_line=on_line,
            )
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(self._failed, str(exc))
            return
        self.app.call_from_thread(self._finished, result)

    def _append(self, line: str) -> None:
        self.query_one("#sweep-log", RichLog).write(line)

    def _finished(self, result: dict) -> None:
        rc = result.get("returncode")
        output = result.get("output_path")
        self._status(f"Sweep finished (code {rc}). Output: {output}")
        self.app.refresh_results()

    def _failed(self, message: str) -> None:
        self._status(f"[red]Sweep failed:[/] {message}")
        self.query_one("#sweep-log", RichLog).write(f"ERROR: {message}")

    def _status(self, message: str) -> None:
        self.query_one("#sweep-status", Static).update(message)
