"""Validation module for NTS simulation configurations."""

from typing import Any

from pydantic import ValidationError

from core.config import BC_LABELS, SimulationConfig, describe_bc


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self, is_valid: bool, errors: list | None = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self):
        return self.is_valid
    
    def __str__(self):
        if self.is_valid:
            return "✓ Configuration is valid"
        else:
            return f"✗ Validation failed with {len(self.errors)} error(s):\n" + \
                   "\n".join(f"  - {err}" for err in self.errors)


def validate(config: dict[str, Any]) -> ValidationResult:
    """
    Validate a configuration dictionary.
    
    Args:
        config: Dictionary containing simulation configuration
        
    Returns:
        ValidationResult object indicating success/failure and any errors
    """
    try:
        # Try to create SimulationConfig from dict
        # This will trigger all Pydantic validators
        SimulationConfig(**config)
        return ValidationResult(is_valid=True)
    
    except ValidationError as e:
        # Extract error messages from Pydantic ValidationError
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        
        return ValidationResult(is_valid=False, errors=errors)
    
    except Exception as e:
        # Catch any other unexpected errors
        return ValidationResult(is_valid=False, errors=[f"Unexpected error: {e!s}"])


def validate_config_object(config: SimulationConfig) -> ValidationResult:
    """
    Validate an already-instantiated SimulationConfig object.
    
    This is useful when you have a config object and want to re-validate it
    after modifications.
    
    Args:
        config: SimulationConfig object
        
    Returns:
        ValidationResult object
    """
    try:
        # Re-validate by converting to dict and back
        config.model_validate(config.model_dump())
        return ValidationResult(is_valid=True)
    
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        
        return ValidationResult(is_valid=False, errors=errors)


def validate_file(filepath: str) -> ValidationResult:
    """
    Validate a configuration file.
    
    Args:
        filepath: Path to JSON configuration file
        
    Returns:
        ValidationResult object
    """
    try:
        SimulationConfig.from_json_file(filepath)
        return ValidationResult(is_valid=True)
    
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        
        return ValidationResult(is_valid=False, errors=errors)
    
    except FileNotFoundError:
        return ValidationResult(is_valid=False, errors=[f"File not found: {filepath}"])
    
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[f"Error reading file: {e!s}"])


def get_validation_summary(config: SimulationConfig) -> str:
    """
    Get a human-readable summary of the configuration.
    
    Args:
        config: SimulationConfig object
        
    Returns:
        Formatted string with configuration summary
    """
    summary = []
    summary.append("Configuration Summary:")
    summary.append(f"  • Discrete ordinates (N): {config.N}")
    summary.append(f"  • Material zones (NZ): {config.NZ}")
    summary.append(
        f"  • X regions: {config.NR_X} "
        f"(total cells: {config.total_nodes_x}, length: {config.total_length_x:g} cm)"
    )
    summary.append(
        f"  • Y regions: {config.NR_Y} "
        f"(total cells: {config.total_nodes_y}, length: {config.total_length_y:g} cm)"
    )
    summary.append(f"  • Tolerance: {config.TOL:.2e}")
    
    # Source strength
    total_source = sum(sum(row) for row in config.QMAP)
    summary.append(f"  • Total source strength: {total_source:.4f}")
    
    # Boundary conditions (canonical order: left, bottom, right, top)
    bc_str = ", ".join(
        f"{label}={describe_bc(value)}"
        for label, value in zip(BC_LABELS, config.BC, strict=True)
    )
    summary.append(f"  • Boundary conditions: {bc_str}")
    
    return "\n".join(summary)
