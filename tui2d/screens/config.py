"""Configuration editor for the 2D workflow."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, Select, Static

from ..models import (
    DEFAULT_SOLVER,
    EVEN_ORDERS,
    SOLVER_NAMES,
    build_preview,
    validate_config,
)
from ..services import config_store
from ..widgets import BCTable, DomainMap, MatrixEditor, RegionTable, ZoneTable

CONFIG_GLOB = "config_2d_*.json"


class Config2DPane(VerticalScroll):
    """Form for the whole 2D configuration with a proportional domain map."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._updating = False
        self._loaded_path: Path | None = None

    # -- layout --------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("2D configuration", classes="title", id="cfg2d-title"),
            Static("", id="cfg2d-status", classes="config-status"),
            classes="config-header",
        )
        yield Horizontal(
            Select([], prompt="Load config...", id="cfg2d-select"),
            Button("Load", id="cfg2d-load"),
            Button("New", id="cfg2d-new"),
            Button("Validate", id="cfg2d-validate"),
            Button("Save", id="cfg2d-save", variant="primary"),
            classes="button-row",
        )
        yield Horizontal(
            Label("File", classes="field-label"),
            Input(
                value=str(config_store.next_config_path()),
                placeholder="outputs/inputs/config_2d_XXX.json",
                id="cfg2d-path",
            ),
            classes="field-row",
        )

        yield Static("Domain", classes="section-title")
        yield Static(
            "Regions keep their physical proportion: a 20 x 10 cm domain is "
            "drawn twice as wide as tall. Colour is the material zone; black "
            "lines separate regions.",
            classes="muted",
        )
        yield DomainMap(id="cfg2d-domain", classes="domain-map")
        yield Static("", id="cfg2d-counts", classes="muted")

        yield Static("Material zones", classes="section-title")
        yield ZoneTable()

        yield Static("X regions", classes="section-title")
        yield RegionTable(prefix="xregion", title="X regions (left to right)")

        yield Static("Y regions", classes="section-title")
        yield RegionTable(prefix="yregion", title="Y regions (bottom to top)")

        yield Static("Zone map (ZMAP)", classes="section-title")
        yield Static(
            "One zone index per region; rows are Y (bottom to top) and "
            "columns are X (left to right). Values must be 1..NZ.",
            classes="muted",
        )
        yield MatrixEditor(
            prefix="zmap",
            title="ZMAP",
            kind="int",
            placeholder="1",
            id="cfg2d-zmap",
        )

        yield Static("Source map (QMAP)", classes="section-title")
        yield Static(
            "External source per region (neutrons/cm3/s or normalized). "
            "Zero is allowed.",
            classes="muted",
        )
        yield MatrixEditor(
            prefix="qmap",
            title="QMAP",
            kind="float",
            placeholder="1.0",
            id="cfg2d-qmap",
        )

        yield Static("Solver settings", classes="section-title")
        yield Horizontal(
            Label("Quadrature order (N)", classes="field-label"),
            Select(
                [(str(value), str(value)) for value in EVEN_ORDERS],
                value="4",
                allow_blank=False,
                id="cfg2d-N",
            ),
            classes="field-row",
        )
        yield Horizontal(
            Label("Tolerance (TOL)", classes="field-label"),
            Input(value="1e-05", placeholder="1e-5", id="cfg2d-TOL"),
            classes="field-row",
        )
        yield Horizontal(
            Label("Preferred solver", classes="field-label"),
            Select(
                [(name, name) for name in SOLVER_NAMES],
                value=DEFAULT_SOLVER,
                allow_blank=False,
                id="cfg2d-solver",
            ),
            classes="field-row",
        )

        yield BCTable(id="cfg2d-bc")

        yield Static("input.txt preview", classes="section-title")
        yield Static(
            "", id="cfg2d-preview", classes="preview-text", markup=False
        )

        self.call_after_refresh(self._after_compose)

    def _after_compose(self) -> None:
        self.refresh_load_options()
        self.populate(config_store.default_config())

    # -- persistence ---------------------------------------------------
    def refresh_load_options(self) -> None:
        options = [(path.name, str(path)) for path in config_store.list_configs()]
        self.query_one("#cfg2d-select", Select).set_options(options)

    def populate(self, config: dict) -> None:
        """Load a configuration dictionary into every widget."""
        self._updating = True
        try:
            zone_names = config.get("ZONE_NAMES") or []
            zones = config.get("zones") or []
            zone_rows = []
            for index, zone in enumerate(zones):
                zone_rows.append(
                    {
                        "name": (
                            zone_names[index]
                            if index < len(zone_names)
                            else zone.get("name", "")
                        ),
                        "sigma_t": zone.get("sigma_t", ""),
                        "sigma_s": zone.get("sigma_s", ""),
                    }
                )
            self.query_one(ZoneTable).set_rows(zone_rows)

            self.query_one("#xregion-table", RegionTable).set_rows(
                [
                    {
                        "length": region.get("length", ""),
                        "cells": region.get("nodes", ""),
                    }
                    for region in config.get("XDOM") or []
                ]
            )
            self.query_one("#yregion-table", RegionTable).set_rows(
                [
                    {
                        "length": region.get("length", ""),
                        "cells": region.get("nodes", ""),
                    }
                    for region in config.get("YDOM") or []
                ]
            )

            self.query_one("#cfg2d-zmap", MatrixEditor).set_values(
                config.get("ZMAP") or [[1]]
            )
            self.query_one("#cfg2d-qmap", MatrixEditor).set_values(
                config.get("QMAP") or [[1.0]]
            )
            self.query_one("#cfg2d-bc", BCTable).set_values(
                config.get("BC") or [0.0, 0.0, 0.0, 0.0]
            )
            try:
                self.query_one("#cfg2d-N", Select).value = str(config.get("N", 4))
            except Exception:  # noqa: BLE001 - keep the previous valid value
                self._status(f"Unsupported N: {config.get('N')!r}")
            self.query_one("#cfg2d-TOL", Input).value = f"{config.get('TOL', 1e-5):g}"
            solver = str(config.get("_solver", DEFAULT_SOLVER))
            if solver in SOLVER_NAMES:
                self.query_one("#cfg2d-solver", Select).value = solver
        finally:
            self._updating = False
        self._refresh_all()

    # -- collection ----------------------------------------------------
    def collect_config(self) -> dict:
        """Build a configuration dictionary from the widgets."""
        zone = self.query_one(ZoneTable)
        names, sigma_t, sigma_s = zone.values()
        zones = [
            {"sigma_t": total, "sigma_s": scatter}
            for total, scatter in zip(sigma_t, sigma_s, strict=True)
        ]

        x_lengths, x_cells = self.query_one("#xregion-table", RegionTable).values()
        y_lengths, y_cells = self.query_one("#yregion-table", RegionTable).values()

        zmap = self.query_one("#cfg2d-zmap", MatrixEditor).values()
        qmap = self.query_one("#cfg2d-qmap", MatrixEditor).values()
        bc = self.query_one("#cfg2d-bc", BCTable).values()

        tol_text = self.query_one("#cfg2d-TOL", Input).value.strip()
        try:
            tol = float(tol_text)
        except ValueError as exc:
            raise ValueError("TOL must be a number.") from exc

        config = {
            "N": int(str(self.query_one("#cfg2d-N", Select).value)),
            "NZ": len(zones),
            "zones": zones,
            "NR_X": len(x_lengths),
            "XDOM": [
                {"length": length, "nodes": cells}
                for length, cells in zip(x_lengths, x_cells, strict=True)
            ],
            "NR_Y": len(y_lengths),
            "YDOM": [
                {"length": length, "nodes": cells}
                for length, cells in zip(y_lengths, y_cells, strict=True)
            ],
            "ZMAP": zmap,
            "QMAP": qmap,
            "BC": bc,
            "TOL": tol,
        }

        filled_names = [str(name).strip() for name in names]
        if any(filled_names):
            if not all(filled_names):
                raise ValueError(
                    "Zone names: fill one name per zone or leave them all blank."
                )
            config["ZONE_NAMES"] = filled_names
        return config

    # -- derived views -------------------------------------------------
    def _refresh_all(self) -> None:
        if self._updating or not self.is_mounted:
            return
        self._sync_matrices()
        self._refresh_domain()
        self._refresh_preview()

    def _sync_matrices(self) -> None:
        try:
            x_rows = len(self.query_one("#xregion-table", RegionTable).as_dicts())
            y_rows = len(self.query_one("#yregion-table", RegionTable).as_dicts())
            zmap = self.query_one("#cfg2d-zmap", MatrixEditor)
            qmap = self.query_one("#cfg2d-qmap", MatrixEditor)
        except Exception:  # noqa: BLE001 - widgets not mounted yet
            return
        self._updating = True
        try:
            zmap.set_size(y_rows, x_rows)
            qmap.set_size(y_rows, x_rows)
        finally:
            self._updating = False

    def _refresh_domain(self) -> None:
        try:
            zones = [
                {
                    "sigma_t": row.get("sigma_t", "?"),
                    "sigma_s": row.get("sigma_s", "?"),
                    "name": row.get("name", ""),
                }
                for row in self.query_one(ZoneTable).as_dicts()
            ]
            xdom = self.query_one("#xregion-table", RegionTable).as_dicts()
            ydom = self.query_one("#yregion-table", RegionTable).as_dicts()
        except Exception:  # noqa: BLE001
            return
        try:
            zmap = self.query_one("#cfg2d-zmap", MatrixEditor).values()
        except ValueError:
            zmap = []
        try:
            bc = self.query_one("#cfg2d-bc", BCTable).values()
        except ValueError:
            bc = None

        self.query_one("#cfg2d-domain", DomainMap).set_data(
            xdom, ydom, zmap, zones, bc
        )
        self.query_one("#cfg2d-counts", Static).update(
            f"Zones: {len(zones)} | X regions: {len(xdom)} | "
            f"Y regions: {len(ydom)} | "
            f"Mesh: {sum(_cells(r) for r in xdom)} x "
            f"{sum(_cells(r) for r in ydom)} cells"
        )

    def _refresh_preview(self) -> None:
        try:
            text = build_preview(self.collect_config(), max_lines=24)
        except Exception as exc:  # noqa: BLE001 - show the message in place
            text = f"# input.txt not available yet: {exc}"
        self.query_one("#cfg2d-preview", Static).update(text)

    # -- status --------------------------------------------------------
    def _status(self, message: str) -> None:
        self.query_one("#cfg2d-status", Static).update(message)

    def solver_name(self) -> str:
        return str(self.query_one("#cfg2d-solver", Select).value)

    # -- actions -------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id
        if button == "cfg2d-load":
            self._load_selected()
        elif button == "cfg2d-new":
            self.populate(config_store.default_config())
            self.query_one("#cfg2d-path", Input).value = str(
                config_store.next_config_path()
            )
            self._loaded_path = None
            self._status("New configuration. Fill the fields and save.")
        elif button == "cfg2d-validate":
            self.validate_current()
        elif button == "cfg2d-save":
            self.save_current()

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._updating:
            return
        if event.select.id == "cfg2d-select" and not event.select.is_blank():
            self._load_selected()
        elif event.select.id in ("cfg2d-N", "cfg2d-solver"):
            self._refresh_all()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._updating:
            return
        if event.input.id == "cfg2d-TOL":
            self._refresh_all()

    def on_zone_table_changed(self, event) -> None:
        self._refresh_all()

    def on_region_table_changed(self, event) -> None:
        self._refresh_all()

    def on_matrix_editor_changed(self, event) -> None:
        if self._updating:
            return
        self._refresh_all()

    def on_bctable_changed(self, event) -> None:
        self._refresh_all()

    def _load_selected(self) -> None:
        select = self.query_one("#cfg2d-select", Select)
        if select.is_blank():
            self._status("Select a configuration file first.")
            return
        path = Path(str(select.value))
        try:
            config = config_store.load_config(path)
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Load failed:[/] {exc}")
            return
        self.populate(config)
        self.query_one("#cfg2d-path", Input).value = str(path)
        self._loaded_path = path
        self._status(f"Loaded {path.name}.")

    def validate_current(self) -> None:
        """Validate the form and show the result in the status line."""
        try:
            config = self.collect_config()
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Form error:[/] {exc}")
            return
        errors, message = validate_config(config)
        if errors:
            self._status("[red]Invalid:[/] " + " | ".join(errors[:3]))
        else:
            self._status(f"[green]{message}[/]")

    def save_current(self, path: Path | str | None = None) -> Path | None:
        """Validate and save the form; return the written path."""
        try:
            config = self.collect_config()
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Save failed:[/] {exc}")
            return None
        errors, message = validate_config(config)
        if errors:
            self._status("[red]Invalid:[/] " + " | ".join(errors[:3]))
            return None

        if path is None:
            text = self.query_one("#cfg2d-path", Input).value.strip()
            path = Path(text) if text else config_store.next_config_path()
        try:
            saved = config_store.save_config(path, config, self.solver_name())
        except Exception as exc:  # noqa: BLE001
            self._status(f"[red]Save failed:[/] {exc}")
            return None

        self._loaded_path = saved
        self.query_one("#cfg2d-path", Input).value = str(saved)
        self.refresh_load_options()
        self._status(f"[green]{message}[/] Saved {saved.name}.")
        return saved


def _cells(region: dict) -> int:
    try:
        return max(0, int(region.get("cells", 0)))
    except (TypeError, ValueError):
        return 0
