"""Configuration data models for NTS simulations using Pydantic."""

import json
from typing import List
from pydantic import BaseModel, Field, field_validator, model_validator


class Zone(BaseModel):
    """Material zone with nuclear cross-sections."""
    
    sigma_t: float = Field(..., gt=0, description="Total cross-section (must be > 0)")
    sigma_s: float = Field(..., ge=0, description="Scattering cross-section (must be >= 0)")
    
    @field_validator('sigma_s')
    @classmethod
    def validate_sigma_s(cls, v, info):
        """Ensure sigma_s < sigma_t."""
        if 'sigma_t' in info.data and v >= info.data['sigma_t']:
            raise ValueError(f"sigma_s ({v}) must be less than sigma_t ({info.data['sigma_t']})")
        return v


class DomainRegion(BaseModel):
    """Spatial domain region definition."""
    
    length: float = Field(..., gt=0, description="Length of region in cm (must be > 0)")
    nodes: int = Field(..., gt=0, description="Number of spatial nodes (must be > 0)")


class SimulationConfig(BaseModel):
    """Complete configuration for an NTS simulation."""
    
    N: int = Field(..., gt=0, description="Number of discrete ordinates")
    NZ: int = Field(..., gt=0, description="Number of material zones")
    zones: List[Zone] = Field(..., description="List of material zones")
    NR_X: int = Field(..., gt=0, description="Number of regions in X direction")
    XDOM: List[DomainRegion] = Field(..., description="X domain regions")
    NR_Y: int = Field(..., gt=0, description="Number of regions in Y direction")
    YDOM: List[DomainRegion] = Field(..., description="Y domain regions")
    ZMAP: List[List[int]] = Field(..., description="Zone map (NR_Y x NR_X)")
    QMAP: List[List[float]] = Field(..., description="Source map (NR_Y x NR_X)")
    BC: List[float] = Field(..., min_length=4, max_length=4, description="Boundary conditions [left, right, bottom, top]")
    TOL: float = Field(..., gt=0, description="Convergence tolerance")
    
    @field_validator('N')
    @classmethod
    def validate_n_even(cls, v):
        """N must be even."""
        if v % 2 != 0:
            raise ValueError(f"N must be even, got {v}")
        return v
    
    @field_validator('TOL')
    @classmethod
    def validate_tol_range(cls, v):
        """TOL must be in reasonable range."""
        if not (1e-7 <= v <= 1e-2):
            raise ValueError(f"TOL must be between 1e-7 and 1e-2, got {v}")
        return v
    
    @field_validator('BC')
    @classmethod
    def validate_bc(cls, v):
        """BC values must be 0.0 (vacuum) or 1.0 (reflective)."""
        for bc_val in v:
            if bc_val not in [0.0, 1.0]:
                raise ValueError(f"BC values must be 0.0 or 1.0, got {bc_val}")
        return v
    
    @model_validator(mode='after')
    def validate_consistency(self):
        """Validate consistency between related fields."""
        # Check zones length
        if len(self.zones) != self.NZ:
            raise ValueError(f"Number of zones ({len(self.zones)}) must equal NZ ({self.NZ})")
        
        # Check XDOM length
        if len(self.XDOM) != self.NR_X:
            raise ValueError(f"XDOM length ({len(self.XDOM)}) must equal NR_X ({self.NR_X})")
        
        # Check YDOM length
        if len(self.YDOM) != self.NR_Y:
            raise ValueError(f"YDOM length ({len(self.YDOM)}) must equal NR_Y ({self.NR_Y})")
        
        # Check ZMAP dimensions
        if len(self.ZMAP) != self.NR_Y:
            raise ValueError(f"ZMAP rows ({len(self.ZMAP)}) must equal NR_Y ({self.NR_Y})")
        for i, row in enumerate(self.ZMAP):
            if len(row) != self.NR_X:
                raise ValueError(f"ZMAP row {i} length ({len(row)}) must equal NR_X ({self.NR_X})")
            for val in row:
                if not (1 <= val <= self.NZ):
                    raise ValueError(f"ZMAP values must be between 1 and NZ ({self.NZ}), got {val}")
        
        # Check QMAP dimensions
        if len(self.QMAP) != self.NR_Y:
            raise ValueError(f"QMAP rows ({len(self.QMAP)}) must equal NR_Y ({self.NR_Y})")
        for i, row in enumerate(self.QMAP):
            if len(row) != self.NR_X:
                raise ValueError(f"QMAP row {i} length ({len(row)}) must equal NR_X ({self.NR_X})")
            for val in row:
                if val < 0:
                    raise ValueError(f"QMAP values must be non-negative, got {val}")
        
        return self
    
    @classmethod
    def from_json_file(cls, filepath: str) -> "SimulationConfig":
        """Load configuration from JSON file, ignoring comment fields."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Remove comment fields (fields starting with '_')
        clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
        
        return cls(**clean_data)
    
    def to_json_file(self, filepath: str):
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
