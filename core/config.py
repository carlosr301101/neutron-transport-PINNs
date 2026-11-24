"""Configuration data models for NTS simulations using Pydantic.

The canonical contract for the 2D C solvers is documented in
``doc/2D_SOLVERS_CONTRACT.md``.  Boundary conditions are ordered
``[left, bottom, right, top]`` and accept ``-1.0`` (reflective), ``0.0``
(vacuum) or any positive value (incoming flux).
"""

import json

from pydantic import BaseModel, Field, field_validator, model_validator

# Boundary-condition labels in the order used by the C solvers.
BC_LABELS = ("Left", "Bottom", "Right", "Top")

# Boundary-condition values understood by the C solvers.
BC_REFLECTIVE = -1.0
BC_VACUUM = 0.0


def describe_bc(value: float) -> str:
    """Return the human-readable kind of a boundary-condition value."""
    if value == BC_REFLECTIVE:
        return "Reflective"
    if value == BC_VACUUM:
        return "Vacuum"
    return "Incoming"


def is_valid_bc(value: float) -> bool:
    """Return True when *value* is a valid C-solver boundary condition."""
    return value in (BC_REFLECTIVE, BC_VACUUM) or value > 0.0


class Zone(BaseModel):
    """Material zone with nuclear cross-sections."""

    sigma_t: float = Field(
        ..., gt=0, description="Total cross-section (must be > 0)"
    )
    sigma_s: float = Field(
        ..., ge=0, description="Scattering cross-section (must be >= 0)"
    )

    @field_validator("sigma_s")
    @classmethod
    def validate_sigma_s(cls, v, info):
        """Ensure sigma_s < sigma_t."""
        if "sigma_t" in info.data and v >= info.data["sigma_t"]:
            raise ValueError(
                f"sigma_s ({v}) must be less than sigma_t ({info.data['sigma_t']})"
            )
        return v


class DomainRegion(BaseModel):
    """Spatial domain region definition."""

    length: float = Field(..., gt=0, description="Length of region in cm (must be > 0)")
    nodes: int = Field(
        ..., ge=3, description="Number of spatial cells (must be >= 3)"
    )


class SimulationConfig(BaseModel):
    """Complete configuration for an NTS simulation."""

    N: int = Field(
        ..., ge=2, le=18, description="Number of discrete ordinates (even, 2-18)"
    )
    NZ: int = Field(..., gt=0, description="Number of material zones")
    zones: list[Zone] = Field(..., description="List of material zones")
    NR_X: int = Field(..., gt=0, description="Number of regions in X direction")
    XDOM: list[DomainRegion] = Field(..., description="X domain regions")
    NR_Y: int = Field(..., gt=0, description="Number of regions in Y direction")
    YDOM: list[DomainRegion] = Field(..., description="Y domain regions")
    ZMAP: list[list[int]] = Field(..., description="Zone map (NR_Y x NR_X)")
    QMAP: list[list[float]] = Field(..., description="Source map (NR_Y x NR_X)")
    BC: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Boundary conditions [left, bottom, right, top]",
    )
    TOL: float = Field(..., gt=0, description="Convergence tolerance")

    @field_validator("N")
    @classmethod
    def validate_n_even(cls, v):
        """N must be even."""
        if v % 2 != 0:
            raise ValueError(f"N must be even, got {v}")
        return v

    @field_validator("TOL")
    @classmethod
    def validate_tol_range(cls, v):
        """TOL must be a small positive number."""
        if not (1e-7 <= v <= 1e-2):
            raise ValueError(f"TOL must be between 1e-7 and 1e-2, got {v}")
        return v

    @field_validator("BC")
    @classmethod
    def validate_bc(cls, v):
        """BC values must be -1.0, 0.0 or > 0.0 (order: left, bottom, right, top)."""
        for bc_val in v:
            if not is_valid_bc(bc_val):
                raise ValueError(
                    "BC values must be -1.0 (reflective), 0.0 (vacuum) or > 0 "
                    f"(incoming flux), got {bc_val} in [left, bottom, right, top]"
                )
        return v

    @model_validator(mode="after")
    def validate_consistency(self):
        """Validate consistency between related fields."""
        # Check zones length
        if len(self.zones) != self.NZ:
            raise ValueError(
                f"Number of zones ({len(self.zones)}) must equal NZ ({self.NZ})"
            )

        # Check XDOM length
        if len(self.XDOM) != self.NR_X:
            raise ValueError(
                f"XDOM length ({len(self.XDOM)}) must equal NR_X ({self.NR_X})"
            )

        # Check YDOM length
        if len(self.YDOM) != self.NR_Y:
            raise ValueError(
                f"YDOM length ({len(self.YDOM)}) must equal NR_Y ({self.NR_Y})"
            )

        # Check ZMAP dimensions
        if len(self.ZMAP) != self.NR_Y:
            raise ValueError(
                f"ZMAP rows ({len(self.ZMAP)}) must equal NR_Y ({self.NR_Y})"
            )
        for i, row in enumerate(self.ZMAP):
            if len(row) != self.NR_X:
                raise ValueError(
                    f"ZMAP row {i} length ({len(row)}) must equal NR_X ({self.NR_X})"
                )
            for val in row:
                if not (1 <= val <= self.NZ):
                    raise ValueError(
                        f"ZMAP values must be between 1 and NZ ({self.NZ}), got {val}"
                    )

        # Check QMAP dimensions
        if len(self.QMAP) != self.NR_Y:
            raise ValueError(
                f"QMAP rows ({len(self.QMAP)}) must equal NR_Y ({self.NR_Y})"
            )
        for i, row in enumerate(self.QMAP):
            if len(row) != self.NR_X:
                raise ValueError(
                    f"QMAP row {i} length ({len(row)}) must equal NR_X ({self.NR_X})"
                )
            for val in row:
                if val < 0:
                    raise ValueError(f"QMAP values must be non-negative, got {val}")

        return self

    @property
    def total_nodes_x(self) -> int:
        """Total number of cells in the X direction."""
        return sum(region.nodes for region in self.XDOM)

    @property
    def total_nodes_y(self) -> int:
        """Total number of cells in the Y direction."""
        return sum(region.nodes for region in self.YDOM)

    @property
    def total_length_x(self) -> float:
        """Total physical length in the X direction (cm)."""
        return sum(region.length for region in self.XDOM)

    @property
    def total_length_y(self) -> float:
        """Total physical length in the Y direction (cm)."""
        return sum(region.length for region in self.YDOM)

    def cell_centers_x(self) -> list[float]:
        """Return the X coordinate (cm) of every cell center."""
        centers = []
        start = 0.0
        for region in self.XDOM:
            dx = region.length / region.nodes
            centers.extend(start + (i + 0.5) * dx for i in range(region.nodes))
            start += region.length
        return centers

    def cell_centers_y(self) -> list[float]:
        """Return the Y coordinate (cm) of every cell center."""
        centers = []
        start = 0.0
        for region in self.YDOM:
            dy = region.length / region.nodes
            centers.extend(start + (i + 0.5) * dy for i in range(region.nodes))
            start += region.length
        return centers

    @classmethod
    def from_json_file(cls, filepath: str) -> SimulationConfig:
        """Load configuration from a UTF-8 JSON file, ignoring comment fields."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Remove comment fields (fields starting with '_')
        clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

        return cls(**clean_data)

    def to_json_file(self, filepath: str):
        """Save configuration to a UTF-8 JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
            f.write("\n")
