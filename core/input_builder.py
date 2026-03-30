"""Input file builder for NTS solvers."""

from pathlib import Path
from core.config import SimulationConfig


class InputBuilder:
    """Builds input.txt files for NTS solvers following the strict format."""
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize the input builder.
        
        Args:
            config: SimulationConfig object with validated configuration
        """
        self.config = config
    
    def build(self) -> str:
        """
        Build the input file content as a string.
        
        Returns:
            String formatted according to NTS input specification
        """
        lines = []
        
        # Line 1: N (number of discrete ordinates)
        lines.append(str(self.config.N))
        
        # Line 2: NZ (number of zones)
        lines.append(str(self.config.NZ))
        
        # Lines 3 to NZ+2: zone data (sigma_t sigma_s)
        for zone in self.config.zones:
            lines.append(f"{zone.sigma_t} {zone.sigma_s}")
        
        # Line NZ+3: NR_X (number of X regions)
        lines.append(str(self.config.NR_X))
        
        # Lines NZ+4 to NZ+3+NR_X: XDOM (length nodes)
        for region in self.config.XDOM:
            lines.append(f"{region.length} {region.nodes}")
        
        # Line NZ+4+NR_X: NR_Y (number of Y regions)
        lines.append(str(self.config.NR_Y))
        
        # Lines NZ+5+NR_X to NZ+4+NR_X+NR_Y: YDOM (length nodes)
        for region in self.config.YDOM:
            lines.append(f"{region.length} {region.nodes}")
        
        # Lines NZ+5+NR_X+NR_Y to NZ+4+NR_X+2*NR_Y: ZMAP (zone map)
        for row in self.config.ZMAP:
            lines.append(" ".join(map(str, row)))
        
        # Lines: QMAP (source map)
        for row in self.config.QMAP:
            lines.append(" ".join(map(str, row)))
        
        # Line: BC (boundary conditions: left right bottom top)
        lines.append(" ".join(map(str, self.config.BC)))
        
        # Last line: TOL (tolerance)
        lines.append(str(self.config.TOL))
        
        return "\n".join(lines)
    
    def save(self, path: str):
        """
        Save the input file to disk.
        
        Args:
            path: File path where input.txt should be saved
            
        Raises:
            IOError: If file cannot be written
        """
        filepath = Path(path)
        
        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'w') as f:
                f.write(self.build())
        except Exception as e:
            raise IOError(f"Failed to write input file to {path}: {str(e)}")
    
    def preview(self, max_lines: int = 20) -> str:
        """
        Get a preview of the input file content.
        
        Args:
            max_lines: Maximum number of lines to show
            
        Returns:
            Preview string
        """
        content = self.build()
        lines = content.split('\n')
        
        if len(lines) <= max_lines:
            return content
        else:
            preview_lines = lines[:max_lines]
            remaining = len(lines) - max_lines
            preview_lines.append(f"... ({remaining} more lines)")
            return "\n".join(preview_lines)


def build_input_from_file(config_file: str, output_file: str):
    """
    Convenience function to build input.txt from a config file.
    
    Args:
        config_file: Path to JSON configuration file
        output_file: Path where input.txt should be saved
    """
    config = SimulationConfig.from_json_file(config_file)
    builder = InputBuilder(config)
    builder.save(output_file)


def build_multiple_inputs(config_files: list, output_dir: str, prefix: str = "input"):
    """
    Build multiple input files from a list of configuration files.
    
    Args:
        config_files: List of paths to JSON configuration files
        output_dir: Directory where input files should be saved
        prefix: Prefix for output filenames (default: "input")
        
    Returns:
        List of generated input file paths
    """
    output_paths = []
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    for i, config_file in enumerate(config_files, start=1):
        output_file = output_dir_path / f"{prefix}_{i:03d}.txt"
        build_input_from_file(config_file, str(output_file))
        output_paths.append(str(output_file))
    
    return output_paths
