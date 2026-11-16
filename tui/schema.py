"""Field metadata for the 1D configuration form.

The TUI builds its widgets from this schema.  Keeping the schema in one place
means every prompt of ``Config.manual_input`` has a matching form field.
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


SECTIONS: tuple[str, ...] = (
    "Geometry",
    "Materials",
    "Angular discretization",
    "Fission and eigenvalue",
    "Source and boundaries",
    "Convergence",
)

FIELDS: tuple[Field, ...] = (
    # Geometry -----------------------------------------------------------
    Field(
        "num_regions",
        "Regions",
        "int",
        "Geometry",
        1,
        help="Number of spatial regions.",
    ),
    Field(
        "num_zones",
        "Material zones",
        "int",
        "Geometry",
        1,
        help="Number of material zones.",
    ),
    Field(
        "NC",
        "Cells per region",
        "list_int",
        "Geometry",
        [1],
        help="Comma-separated; length = regions.",
    ),
    Field(
        "HR",
        "Thickness per region [cm]",
        "list_float",
        "Geometry",
        [10.0],
        help="Comma-separated; length = regions.",
    ),
    Field(
        "IZL",
        "Zone of each region",
        "list_int",
        "Geometry",
        [1],
        help="Comma-separated 1-based zone IDs; length = regions.",
    ),
    # Materials ----------------------------------------------------------
    Field(
        "SCT",
        "Sigma_t per zone [cm^-1]",
        "list_float",
        "Materials",
        [1.0],
        help="Comma-separated; length = zones.",
    ),
    Field(
        "SCS",
        "Sigma_s0 per zone [cm^-1]",
        "list_float",
        "Materials",
        [0.9],
        help="Comma-separated; length = zones.",
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
    # Fission ------------------------------------------------------------
    Field(
        "NU_SIGF",
        "nu*Sigma_f per zone [cm^-1]",
        "list_float",
        "Fission and eigenvalue",
        [0.0],
        help="Comma-separated; length = zones. Zero for no fission.",
    ),
    Field(
        "SIGMA_F",
        "Sigma_f per zone [cm^-1]",
        "optional_list_float",
        "Fission and eigenvalue",
        None,
        help="Optional; only for power normalization.",
    ),
    Field(
        "MODE",
        "Mode",
        "select",
        "Fission and eigenvalue",
        "fixed_source",
        choices=("fixed_source", "eigenvalue", "fixed_k", "driven"),
        allow_blank=True,
        help="Blank lets the solver infer the mode.",
    ),
    Field(
        "K_EFF",
        "Imposed k_eff",
        "optional_float",
        "Fission and eigenvalue",
        None,
        help="Required by fixed_k; forbidden by eigenvalue.",
    ),
    Field(
        "TOL_K",
        "k_eff tolerance",
        "float",
        "Fission and eigenvalue",
        1e-6,
    ),
    Field(
        "MAX_OUTER",
        "Max outer iterations",
        "int",
        "Fission and eigenvalue",
        200,
    ),
    Field(
        "K0",
        "Initial k guess",
        "optional_float",
        "Fission and eigenvalue",
        None,
        help="Blank uses the integral estimate.",
    ),
    Field(
        "POWER_KW",
        "Power [kW]",
        "optional_float",
        "Fission and eigenvalue",
        None,
        help="Blank disables power normalization.",
    ),
    Field(
        "E_F_MEV",
        "Energy per fission [MeV]",
        "float",
        "Fission and eigenvalue",
        200.0,
    ),
    Field(
        "NU",
        "Neutrons per fission",
        "optional_float",
        "Fission and eigenvalue",
        None,
        help="Used only to derive Sigma_f from nu*Sigma_f.",
    ),
    Field(
        "AREA_CM2",
        "Cross-section area [cm^2]",
        "float",
        "Fission and eigenvalue",
        1.0,
    ),
    # Source and boundaries ---------------------------------------------
    Field(
        "Q",
        "External source per region",
        "list_float",
        "Source and boundaries",
        [0.0],
        help="Comma-separated; length = regions.",
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
        help="Comma-separated; length = N/2 when the left side is vacuum.",
    ),
    Field(
        "bound_right",
        "Incoming flux right",
        "list_float",
        "Source and boundaries",
        [0.0],
        help="Comma-separated; length = N/2 when the right side is vacuum.",
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
