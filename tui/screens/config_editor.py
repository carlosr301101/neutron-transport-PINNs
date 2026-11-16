"""Configuration editor for the full 1D wizard."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, Switch

from ..models import (
    config_from_form,
    format_field,
    form_values_from_config,
    normalize_boundary,
)
from ..schema import (
    DEFAULT_CONFIG,
    FIELD_BY_KEY,
    FIELDS,
    SECTIONS,
    Field,
    field_visible,
    fields_for_section,
)
from ..services.config_store import (
    list_configs,
    load_config,
    next_config_path,
    save_config,
    validate_config,
)
from ..widgets import FissionTable, GeometryBar, RegionTable, ZoneTable


class ConfigEditorPane(VerticalScroll):
    """Schema-driven form with editable tables and conditional physics fields."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._widgets: dict[str, Widget] = {}
        self._rows: dict[str, Horizontal] = {}
        self._mode = "fixed_source"
        self._updating = False
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

        yield Static("Geometry and materials", classes="section-title")
        yield Static(
            "Regions are drawn proportionally to their thickness; "
            "colour identifies the material zone.",
            classes="muted",
        )
        yield GeometryBar(id="geometry-bar", classes="geometry-bar")
        yield Static("", id="geometry-counts", classes="muted")
        yield RegionTable(id="region-table")
        yield ZoneTable(can_remove=self._can_remove_zone, id="zone-table")

        yield Static("Physics mode", classes="section-title")
        yield self._build_row(FIELD_BY_KEY["MODE"])
        yield Static("", id="mode-note", classes="mode-note")
        yield Vertical(
            FissionTable(id="fission-table"),
            id="fission-wrap",
            classes="fission-wrap",
        )
        for field in fields_for_section("Physics mode"):
            if field.key == "MODE" or field.widget in {"table", "derived"}:
                continue
            yield self._build_row(field)

        for section in SECTIONS[2:]:
            yield Static(section, classes="section-title")
            for field in fields_for_section(section):
                if field.widget in {"table", "derived"}:
                    continue
                yield self._build_row(field)

        yield Static("", id="cfg-status", classes="status")

    def on_mount(self) -> None:
        self._refresh_load_options()
        self._populate(DEFAULT_CONFIG)

    def _build_row(self, field: Field) -> Horizontal:
        widget = self._build_widget(field)
        self._widgets[field.key] = widget
        row = Horizontal(
            Label(field.label, classes="field-label"),
            widget,
            classes="field-row",
            id=f"row-{field.key}",
        )
        self._rows[field.key] = row
        return row

    def _build_widget(self, field: Field) -> Widget:
        widget_id = f"cfg-{field.key}"
        if field.kind == "bool":
            return Switch(value=bool(field.default), id=widget_id)
        if field.kind == "select":
            value = field.default if field.default is not None else Select.NULL
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

    def _infer_mode(self, config: dict) -> str:
        mode = config.get("MODE")
        if mode in ("fixed_source", "eigenvalue", "fixed_k", "driven"):
            return str(mode)
        nusf = config.get("NU_SIGF") or []
        has_fission = any(
            isinstance(value, (int, float)) and value > 0 for value in nusf
        )
        if has_fission:
            return "fixed_k" if config.get("K_EFF") is not None else "eigenvalue"
        return "fixed_source"

    def _populate(self, config: dict) -> None:
        self._updating = True
        try:
            values = form_values_from_config(config)
            for field in FIELDS:
                widget = self._widgets.get(field.key)
                if widget is None:
                    continue
                value = values[field.key]
                if isinstance(widget, Switch):
                    widget.value = bool(value)
                elif isinstance(widget, Select):
                    text = "" if value in (None, "") else str(value)
                    if not text:
                        if field.allow_blank:
                            widget.clear()
                        continue
                    try:
                        widget.value = text
                    except Exception:  # noqa: BLE001 - value not in options
                        if field.allow_blank:
                            widget.clear()
                else:
                    widget.value = "" if value is None else str(value)

            region = self.query_one(RegionTable)
            zone = self.query_one(ZoneTable)
            fission = self.query_one(FissionTable)
            region.set_values(
                config.get("NC") or [],
                config.get("HR") or [],
                config.get("IZL") or [],
                config.get("Q") or [],
            )
            zone.set_values(config.get("SCT") or [], config.get("SCS") or [])
            fission.set_zone_count(zone.zone_count)
            fission.set_values(
                config.get("NU_SIGF") or [],
                config.get("SIGMA_F"),
            )

            mode = self._infer_mode(config)
            self._widgets["MODE"].value = mode
        finally:
            self._updating = False
        self._apply_mode(sanitize=False)
        self._refresh_geometry()

    def _collect(self) -> dict:
        raw: dict[str, object] = {}
        for field in FIELDS:
            widget = self._widgets.get(field.key)
            if widget is None:
                continue
            if isinstance(widget, Switch):
                raw[field.key] = widget.value
            elif isinstance(widget, Select):
                raw[field.key] = "" if widget.is_blank() else widget.value
            else:
                raw[field.key] = widget.value

        config = config_from_form(raw)
        region = self.query_one(RegionTable)
        zone = self.query_one(ZoneTable)
        fission = self.query_one(FissionTable)

        nc, hr, izl, q = region.values()
        sct, scs = zone.values()
        nusf, sigmaf = fission.values()
        config.update(
            {
                "num_regions": len(nc),
                "num_zones": len(sct),
                "NC": nc,
                "HR": hr,
                "IZL": izl,
                "SCT": sct,
                "SCS": scs,
                "Q": q,
                "NU_SIGF": nusf,
                "SIGMA_F": sigmaf,
            }
        )

        n_half = int(config["N"]) // 2
        if config.get("reflex_izq"):
            config["bound_left"] = [0.0] * n_half
        else:
            config["bound_left"] = normalize_boundary(config.get("bound_left"), n_half)
        if config.get("reflex_der"):
            config["bound_right"] = [0.0] * n_half
        else:
            config["bound_right"] = normalize_boundary(
                config.get("bound_right"), n_half
            )

        mode = config.get("MODE") or "fixed_source"
        if mode == "fixed_source":
            config.update(
                {
                    "NU_SIGF": [0.0] * len(sct),
                    "SIGMA_F": None,
                    "K_EFF": None,
                    "K0": None,
                    "POWER_KW": None,
                }
            )
        elif mode == "eigenvalue":
            config["K_EFF"] = None
            config["Q"] = [0.0] * len(nc)
        elif mode == "driven":
            config["K_EFF"] = None
            config["K0"] = None
        return config

    def _apply_mode(self, sanitize: bool) -> None:
        select = self._widgets.get("MODE")
        mode = (
            "fixed_source" if select is None or select.is_blank() else str(select.value)
        )
        self._mode = mode

        for field in FIELDS:
            row = self._rows.get(field.key)
            if row is not None:
                row.display = field_visible(field, mode)

        self.query_one("#fission-wrap", Vertical).display = mode != "fixed_source"
        self.query_one(RegionTable).set_source_visible(mode != "eigenvalue")
        self.query_one("#mode-note", Static).update(self._mode_note(mode))
        self._apply_reflection_visibility()
        if sanitize:
            self._sanitize_mode(mode)
        self._refresh_geometry()

    @staticmethod
    def _mode_note(mode: str) -> str:
        return {
            "fixed_source": (
                "Fixed source: fission disabled. NU_SIGF is saved as zero "
                "and no fission table is needed."
            ),
            "eigenvalue": (
                "Eigenvalue: computes k_eff. K_EFF is not allowed and the "
                "external source is forced to zero."
            ),
            "fixed_k": ("fixed_k: K_EFF is required. The external source is optional."),
            "driven": (
                "driven: physical k = 1. An external source or incoming flux "
                "is required."
            ),
        }.get(mode, "")

    def _clear_input(self, key: str) -> None:
        widget = self._widgets.get(key)
        if isinstance(widget, Input):
            widget.value = ""

    def _sanitize_mode(self, mode: str) -> None:
        zone = self.query_one(ZoneTable)
        fission = self.query_one(FissionTable)
        if mode == "fixed_source":
            fission.set_zone_count(zone.zone_count)
            fission.set_values([0.0] * zone.zone_count, None)
            self._clear_input("K_EFF")
            self._clear_input("K0")
            self._clear_input("POWER_KW")
        elif mode == "eigenvalue":
            self._clear_input("K_EFF")
            try:
                region = self.query_one(RegionTable)
                nc, hr, izl, _ = region.values()
                region.set_values(nc, hr, izl, [0.0] * len(nc))
            except Exception:  # noqa: BLE001 - leave values for validation
                pass
        elif mode == "driven":
            self._clear_input("K_EFF")
            self._clear_input("K0")

    def _refresh_geometry(self) -> None:
        try:
            region = self.query_one(RegionTable)
            zone = self.query_one(ZoneTable)
            bar = self.query_one(GeometryBar)
            counts = self.query_one("#geometry-counts", Static)
        except Exception:  # noqa: BLE001 - not mounted yet
            return
        regions = region.as_dicts()
        zones = zone.as_dicts()
        bar.set_data(regions, zones)
        counts.update(f"Regions: {len(regions)} | Zones: {len(zones)}")

    def _can_remove_zone(self, index: int) -> bool:
        try:
            region = self.query_one(RegionTable)
        except Exception:  # noqa: BLE001
            return True
        for row in region.as_dicts():
            try:
                if int(row["zone"]) == index + 1:
                    return False
            except TypeError, ValueError:
                continue
        return True

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
        elif event.select.id == "cfg-MODE":
            self._apply_mode(sanitize=True)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id in ("cfg-reflex_izq", "cfg-reflex_der"):
            self._apply_reflection_visibility()

    def _apply_reflection_visibility(self) -> None:
        left = self._widgets.get("reflex_izq")
        right = self._widgets.get("reflex_der")
        if "bound_left" in self._rows:
            self._rows["bound_left"].display = not (
                isinstance(left, Switch) and left.value
            )
        if "bound_right" in self._rows:
            self._rows["bound_right"].display = not (
                isinstance(right, Switch) and right.value
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._updating:
            return
        input_id = event.input.id or ""
        if input_id.startswith("region-") or input_id.startswith("zone-"):
            self._refresh_geometry()

    def on_region_table_changed(self, event) -> None:
        self._refresh_geometry()

    def on_zone_table_changed(self, event) -> None:
        try:
            zone = self.query_one(ZoneTable)
            fission = self.query_one(FissionTable)
            fission.set_zone_count(zone.zone_count)
        except Exception:  # noqa: BLE001
            pass
        self._refresh_geometry()

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
