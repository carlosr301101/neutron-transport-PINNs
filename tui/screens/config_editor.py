"""Configuration editor for the full 1D wizard."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, Switch

from ..models import config_from_form, format_field, form_values_from_config
from ..schema import (
    DEFAULT_CONFIG,
    FIELDS,
    SECTIONS,
    Field,
    fields_for_section,
)
from ..services.config_store import (
    list_configs,
    load_config,
    next_config_path,
    save_config,
    validate_config,
)


class ConfigEditorPane(VerticalScroll):
    """Schema-driven form covering every field of the 1D configuration."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._widgets: dict[str, Widget] = {}
        self._loaded_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Static("Configuration wizard", classes="title")
        yield Horizontal(
            Select([], prompt="Load config...", id="cfg-select"),
            Button("Load", id="cfg-load"),
            Button("New", id="cfg-new"),
            Button("Validate", id="cfg-validate"),
            Button("Save", id="cfg-save", variant="primary"),
            classes="button-row",
        )
        yield Horizontal(
            Label("File", classes="field-label"),
            Input(
                value=str(next_config_path()),
                placeholder="outputs/inputs/config_1d_XXX.json",
                id="cfg-path",
            ),
            classes="field-row",
        )

        for section in SECTIONS:
            yield Static(section, classes="section-title")
            for field in fields_for_section(section):
                widget = self._build_widget(field)
                self._widgets[field.key] = widget
                yield Horizontal(
                    Label(field.label, classes="field-label"),
                    widget,
                    classes="field-row",
                )

        yield Static("", id="cfg-status", classes="status")

    def on_mount(self) -> None:
        self._refresh_load_options()
        self._populate(DEFAULT_CONFIG)

    def _build_widget(self, field: Field) -> Widget:
        widget_id = f"cfg-{field.key}"
        if field.kind == "bool":
            return Switch(value=bool(field.default), id=widget_id)
        if field.kind == "select":
            value = field.default if field.default is not None else Select.BLANK
            return Select(
                [(choice, choice) for choice in field.choices],
                value=value,
                allow_blank=field.allow_blank,
                id=widget_id,
            )
        return Input(
            value=format_field(field, field.default),
            placeholder=field.help,
            id=widget_id,
        )

    def _refresh_load_options(self) -> None:
        options = [(path.name, str(path)) for path in list_configs()]
        select = self.query_one("#cfg-select", Select)
        select.set_options(options)

    def _populate(self, config: dict) -> None:
        values = form_values_from_config(config)
        for field in FIELDS:
            widget = self._widgets[field.key]
            value = values[field.key]
            if isinstance(widget, Switch):
                widget.value = bool(value)
            elif isinstance(widget, Select):
                text = "" if value in (None, "") else str(value)
                if not text:
                    widget.clear()
                    continue
                try:
                    widget.value = text
                except Exception:  # noqa: BLE001 - value not in options
                    widget.clear()
            else:
                widget.value = "" if value is None else str(value)

    def _collect(self) -> dict:
        raw: dict[str, object] = {}
        for field in FIELDS:
            widget = self._widgets[field.key]
            if isinstance(widget, Switch):
                raw[field.key] = widget.value
            elif isinstance(widget, Select):
                raw[field.key] = "" if widget.is_blank() else widget.value
            else:
                raw[field.key] = widget.value
        return config_from_form(raw)

    def _path(self) -> Path:
        text = self.query_one("#cfg-path", Input).value.strip()
        return Path(text) if text else next_config_path()

    def _status(self, message: str) -> None:
        self.query_one("#cfg-status", Static).update(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "cfg-load":
            self._load_selected()
        elif button == "cfg-new":
            self._populate(DEFAULT_CONFIG)
            self.query_one("#cfg-path", Input).value = str(next_config_path())
            self._loaded_path = None
            self._status("New configuration. Fill the fields and save.")
        elif button == "cfg-validate":
            self._validate()
        elif button == "cfg-save":
            self._save()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "cfg-select" and not event.select.is_blank():
            self._load_selected()

    def _load_selected(self) -> None:
        select = self.query_one("#cfg-select", Select)
        if select.is_blank():
            self._status("Select a configuration file first.")
            return
        path = Path(str(select.value))
        try:
            config = load_config(path)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Load failed:[/] {exc}")
            return
        self._populate(config)
        self.query_one("#cfg-path", Input).value = str(path)
        self._loaded_path = path
        self._status(f"Loaded {path}.")

    def _validate(self) -> None:
        try:
            config = self._collect()
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Form error:[/] {exc}")
            return
        errors, message = validate_config(config)
        if errors:
            self._status("[red]Invalid:[/] " + " | ".join(errors))
        else:
            self._status(message)

    def _save(self) -> None:
        try:
            config = self._collect()
            path = self._path()
            saved = save_config(path, config)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Save failed:[/] {exc}")
            return
        self._loaded_path = saved
        self.query_one("#cfg-path", Input).value = str(saved)
        self._refresh_load_options()
        self._status(f"Saved {saved}.")
