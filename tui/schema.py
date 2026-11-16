"""Field metadata for the 1D configuration form.

The TUI builds its widgets from this schema.  Keeping the schema in one place
means every prompt of ``Config.manual_input`` has a matching form field.
Fields with ``widget="table"`` are rendered by a dedicated editable table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Field kinds:
#   int, float, optional_float, text, bool, select,
#   list_int, list_float, optional_list_float
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str
    section: str
    default: Any = None
    choices: tuple[str, ...] = ()
    help: str = ""
    allow_blank: bool = False
    widget: str = "input"
    visible_in: tuple[str, ...] | None = None


SECTIONS: tuple[str, ...] = (
    "Geometry and materials",
    "Physics mode",
    "Angular discretization",
    "Source and boundaries",
    "Convergence",
)

FISSION_MODES: tuple[str, ...] = ("eigenvalue", "fixed_k", "driven")

FIELDS: tuple[Field, ...] = (
    # Geometry and materials --------------------------------------------
    Field(
        "num_regions",
        "Regions",
        "int",
        "Geometry and materials",
        1,
        help="Derived from the region table.",
        widget="derived",
    ),
    Field(
        "num_zones",
        "Material zones",
        "int",
        "Geometry and materials",
        1,
        help="Derived from the zone table.",
        widget="derived",
    ),
    Field(
        "NC",
        "Cells per region",
        "list_int",
        "Geometry and materials",
        [1],
        help="Edited in the region table.",
        widget="table",
    ),
    Field(
        "HR",
        "Thickness per region [cm]",
        "list_float",
        "Geometry and materials",
        [10.0],
        help="Edited in the region table.",
        widget="table",
    ),
    Field(
        "IZL",
        "Zone of each region",
        "list_int",
        "Geometry and materials",
        [1],
        help="Edited in the region table.",
        widget="table",
    ),
    Field(
        "SCT",
        "Sigma_t per zone [cm^-1]",
        "list_float",
        "Geometry and materials",
        [1.0],
        help="Edited in the zone table.",
        widget="table",
    ),
    Field(
        "SCS",
        "Sigma_s0 per zone [cm^-1]",
        "list_float",
        "Geometry and materials",
        [0.9],
        help="Edited in the zone table.",
        widget="table",
    ),
    # Physics mode -------------------------------------------------------
    Field(
        "MODE",
        "Mode",
        "select",
        "Physics mode",
        "fixed_source",
        choices=("fixed_source", "eigenvalue", "fixed_k", "driven"),
        help="fixed_source disables fission.",
    ),
    Field(
        "NU_SIGF",
        "nu*Sigma_f per zone [cm^-1]",
        "list_float",
        "Physics mode",
        [0.0],
        help="Edited in the fission table.",
        widget="table",
        visible_in=FISSION_MODES,
    ),
    Field(
        "SIGMA_F",
        "Sigma_f per zone [cm^-1]",
        "optional_list_float",
        "Physics mode",
        None,
        help="Optional; only for power normalization.",
        widget="table",
        visible_in=FISSION_MODES,
    ),
    Field(
        "K_EFF",
        "Imposed k_eff",
        "optional_float",
        "Physics mode",
        None,
        help="Required by fixed_k; forbidden by eigenvalue.",
        visible_in=("fixed_k",),
    ),
    Field(
        "TOL_K",
        "k_eff tolerance",
        "float",
        "Physics mode",
        1e-6,
        visible_in=FISSION_MODES,
    ),
    Field(
        "MAX_OUTER",
        "Max outer iterations",
        "int",
        "Physics mode",
        200,
        visible_in=FISSION_MODES,
    ),
    Field(
        "K0",
        "Initial k guess",
        "optional_float",
        "Physics mode",
        None,
        help="Blank uses the integral estimate.",
        visible_in=("eigenvalue",),
    ),
    Field(
        "POWER_KW",
        "Power [kW]",
        "optional_float",
        "Physics mode",
        None,
        help="Blank disables power normalization.",
        visible_in=FISSION_MODES,
    ),
    Field(
        "E_F_MEV",
        "Energy per fission [MeV]",
        "float",
        "Physics mode",
        200.0,
        visible_in=FISSION_MODES,
    ),
    Field(
        "NU",
        "Neutrons per fission",
        "optional_float",
        "Physics mode",
        None,
        help="Used only to derive Sigma_f from nu*Sigma_f.",
        visible_in=FISSION_MODES,
    ),
    Field(
        "AREA_CM2",
        "Cross-section area [cm^2]",
        "float",
        "Physics mode",
        1.0,
        visible_in=FISSION_MODES,
    ),
    # Angular ------------------------------------------------------------
    Field(
        "N",
        "Quadrature order",
        "int",
        "Angular discretization",
        2,
        help="Even order: 2, 4, 6 or 8.",
    ),
    Field(
        "SPATIAL_SCHEME",
        "Spatial scheme",
        "select",
        "Angular discretization",
        "DD",
        choices=("DD", "STEP", "SC"),
    ),
    # Source and boundaries ---------------------------------------------
    Field(
        "Q",
        "External source per region",
        "list_float",
        "Source and boundaries",
        [0.0],
        help="Edited in the region table.",
        widget="table",
    ),
    Field(
        "reflex_izq",
        "Reflective left",
        "bool",
        "Source and boundaries",
        False,
    ),
    Field(
        "reflex_der",
        "Reflective right",
        "bool",
        "Source and boundaries",
        False,
    ),
    Field(
        "bound_left",
        "Incoming flux left",
        "list_float",
        "Source and boundaries",
        [0.0],
        help="One scalar expands to N/2 values, or enter N/2 comma-separated values.",
    ),
    Field(
        "bound_right",
        "Incoming flux right",
        "list_float",
        "Source and boundaries",
        [0.0],
        help="One scalar expands to N/2 values, or enter N/2 comma-separated values.",
    ),
    # Convergence --------------------------------------------------------
    Field(
        "epsilon",
        "Flux tolerance",
        "float",
        "Convergence",
        1e-5,
    ),
    Field(
        "max_iter",
        "Max inner iterations",
        "int",
        "Convergence",
        2000,
    ),
)

FIELD_BY_KEY: dict[str, Field] = {field.key: field for field in FIELDS}

DEFAULT_CONFIG: dict[str, Any] = {field.key: field.default for field in FIELDS}


def fields_for_section(section: str) -> tuple[Field, ...]:
    """Fields belonging to *section*, preserving declaration order."""
    return tuple(field for field in FIELDS if field.section == section)


def field_visible(field: Field, mode: str) -> bool:
    """True when *field* is relevant for *mode*."""
    return field.visible_in is None or mode in field.visible_in
