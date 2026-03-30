"""Path management utilities for NTS automation."""

from pathlib import Path
from typing import Optional


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Solver directories
SOLVERS_DIR = PROJECT_ROOT / "solvers" / "runners"

# Output directories
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
INPUTS_DIR = OUTPUTS_DIR / "inputs"
RESULTS_DIR = OUTPUTS_DIR / "results"
LOGS_DIR = OUTPUTS_DIR / "logs"

# Template directory
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Available solver names
AVAILABLE_SOLVERS = ["NTS_DD", "NTS_LD", "NTS_RM_CN", "NTS_RM_LLN"]


def get_solver_path(solver_name: str) -> Path:
    """
    Get the full path to a solver binary.
    
    Args:
        solver_name: Name of the solver (e.g., 'NTS_DD')
        
    Returns:
        Path to solver binary
        
    Raises:
        ValueError: If solver name is not recognized
        FileNotFoundError: If solver binary doesn't exist
    """
    if solver_name not in AVAILABLE_SOLVERS:
        raise ValueError(f"Unknown solver '{solver_name}'. Available: {AVAILABLE_SOLVERS}")
    
    solver_path = SOLVERS_DIR / solver_name
    
    if not solver_path.exists():
        raise FileNotFoundError(f"Solver binary not found: {solver_path}")
    
    if not solver_path.is_file():
        raise FileNotFoundError(f"Solver path is not a file: {solver_path}")
    
    return solver_path


def get_input_path(index: int) -> Path:
    """
    Get the path for an input file by index.
    
    Args:
        index: Input file index (1-based)
        
    Returns:
        Path to input file (e.g., outputs/inputs/input_001.txt)
    """
    return INPUTS_DIR / f"input_{index:03d}.txt"


def get_output_path(index: int) -> Path:
    """
    Get the path for an output file by index.
    
    Args:
        index: Output file index (1-based)
        
    Returns:
        Path to output file (e.g., outputs/results/output_001.json)
    """
    return RESULTS_DIR / f"output_{index:03d}.json"


def get_next_input_index() -> int:
    """
    Get the next available input file index.
    
    Returns:
        Next available index (1-based)
    """
    if not INPUTS_DIR.exists():
        return 1
    
    existing_inputs = list(INPUTS_DIR.glob("input_*.txt"))
    
    if not existing_inputs:
        return 1
    
    # Extract indices from filenames
    indices = []
    for path in existing_inputs:
        try:
            # Extract number from filename like "input_001.txt"
            num_str = path.stem.split('_')[1]
            indices.append(int(num_str))
        except (IndexError, ValueError):
            continue
    
    return max(indices) + 1 if indices else 1


def list_input_files() -> list[Path]:
    """
    List all input files in the inputs directory.
    
    Returns:
        Sorted list of input file paths
    """
    if not INPUTS_DIR.exists():
        return []
    
    return sorted(INPUTS_DIR.glob("input_*.txt"))


def list_output_files() -> list[Path]:
    """
    List all output files in the results directory.
    
    Returns:
        Sorted list of output file paths
    """
    if not RESULTS_DIR.exists():
        return []
    
    return sorted(RESULTS_DIR.glob("output_*.json"))


def ensure_directories():
    """
    Ensure all required directories exist.
    Creates directories if they don't exist.
    """
    directories = [
        OUTPUTS_DIR,
        INPUTS_DIR,
        RESULTS_DIR,
        LOGS_DIR,
        TEMPLATES_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def verify_solver_binaries() -> dict[str, bool]:
    """
    Verify that all solver binaries exist.
    
    Returns:
        Dictionary mapping solver names to existence status
    """
    status = {}
    
    for solver in AVAILABLE_SOLVERS:
        solver_path = SOLVERS_DIR / solver
        status[solver] = solver_path.exists() and solver_path.is_file()
    
    return status


def get_missing_solvers() -> list[str]:
    """
    Get list of missing solver binaries.
    
    Returns:
        List of solver names that are missing
    """
    status = verify_solver_binaries()
    return [solver for solver, exists in status.items() if not exists]


def get_template_path(template_name: str = "base_input.json") -> Path:
    """
    Get path to a configuration template.
    
    Args:
        template_name: Name of the template file
        
    Returns:
        Path to template file
    """
    return TEMPLATES_DIR / template_name


def get_config_path(config_name: str) -> Path:
    """
    Get path for a configuration file.
    
    Args:
        config_name: Name of the configuration (without .json extension)
        
    Returns:
        Path to configuration file
    """
    if not config_name.endswith('.json'):
        config_name += '.json'
    
    return TEMPLATES_DIR / config_name


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename


def get_relative_path(path: Path, base: Optional[Path] = None) -> str:
    """
    Get relative path string from base directory.
    
    Args:
        path: Path to convert
        base: Base directory (default: PROJECT_ROOT)
        
    Returns:
        Relative path string
    """
    if base is None:
        base = PROJECT_ROOT
    
    try:
        return str(path.relative_to(base))
    except ValueError:
        # If path is not relative to base, return absolute path
        return str(path.absolute())
