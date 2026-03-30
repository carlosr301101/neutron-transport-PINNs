"""Solver execution module for running NTS solvers."""

import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
from utils.logger import SimulationLogger, get_logger
from utils.paths import get_solver_path


class SolverResult:
    """Result of a solver execution."""
    
    def __init__(
        self,
        success: bool,
        exit_code: int,
        duration: float,
        stdout: str = "",
        stderr: str = "",
        error_message: str = ""
    ):
        self.success = success
        self.exit_code = exit_code
        self.duration = duration
        self.stdout = stdout
        self.stderr = stderr
        self.error_message = error_message
    
    def __bool__(self):
        return self.success
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"SolverResult(status={status}, exit_code={self.exit_code}, duration={self.duration:.2f}s)"


def run_solver(
    executable: str,
    input_file: str,
    output_file: str,
    timeout: Optional[int] = 3600,
    simulation_id: Optional[str] = None
) -> SolverResult:
    """
    Run an NTS solver with the given input file.
    
    Args:
        executable: Path to solver executable or solver name
        input_file: Path to input file
        output_file: Path where output should be saved
        timeout: Maximum execution time in seconds (default: 3600 = 1 hour)
        simulation_id: Optional simulation ID for logging
        
    Returns:
        SolverResult object with execution details
    """
    logger = get_logger()
    
    # Generate simulation ID if not provided
    if simulation_id is None:
        simulation_id = f"{int(time.time())}"
    
    # Create simulation logger
    sim_logger = SimulationLogger(simulation_id)
    
    try:
        # Resolve solver path
        solver_path = Path(executable)
        if not solver_path.exists():
            # Try to get from solvers directory
            solver_path = get_solver_path(executable)
        
        # Verify input file exists
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Create output directory if needed
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Log simulation start
        sim_logger.start(str(solver_path.name), str(input_path), str(output_path))
        
        # Start timer
        start_time = time.time()
        
        # Run solver with input file as argument (not stdin)
        # Command format: NTS_DD input_001.txt
        with open(output_file, 'w') as outfile:
            process = subprocess.run(
                [str(solver_path), str(input_path)],
                stdout=outfile,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Check result
        success = process.returncode == 0
        
        # Log stderr if any
        if process.stderr:
            for line in process.stderr.split('\n'):
                if line.strip():
                    sim_logger.log_stderr(line)
        
        # Log completion
        status = "completed" if success else "failed"
        sim_logger.end(status, process.returncode)
        
        if success:
            pass  # Success logged to file
        else:
            logger.error(f"Solver failed with exit code {process.returncode}")
        
        return SolverResult(
            success=success,
            exit_code=process.returncode,
            duration=duration,
            stderr=process.stderr
        )
    
    except subprocess.TimeoutExpired:
        duration = timeout
        error_msg = f"Solver execution timed out after {timeout} seconds"
        logger.error(error_msg)
        sim_logger.end("timeout", -1)
        
        return SolverResult(
            success=False,
            exit_code=-1,
            duration=duration,
            error_message=error_msg
        )
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        sim_logger.end("error", -1)
        
        return SolverResult(
            success=False,
            exit_code=-1,
            duration=0.0,
            error_message=str(e)
        )
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        sim_logger.end("error", -1)
        
        return SolverResult(
            success=False,
            exit_code=-1,
            duration=0.0,
            error_message=error_msg
        )


def run_solver_simple(solver_name: str, input_file: str, output_file: str) -> bool:
    """
    Simplified interface to run a solver.
    
    Args:
        solver_name: Name of the solver (e.g., 'NTS_DD')
        input_file: Path to input file
        output_file: Path for output file
        
    Returns:
        True if successful, False otherwise
    """
    result = run_solver(solver_name, input_file, output_file)
    return result.success


def validate_solver_output(output_file: str) -> bool:
    """
    Validate that a solver output file exists and is not empty.
    
    Args:
        output_file: Path to output file
        
    Returns:
        True if valid, False otherwise
    """
    output_path = Path(output_file)
    
    if not output_path.exists():
        return False
    
    if output_path.stat().st_size == 0:
        return False
    
    return True


def estimate_runtime(input_file: str) -> float:
    """
    Estimate solver runtime based on problem size.
    This is a rough heuristic and may not be accurate.
    
    Args:
        input_file: Path to input file
        
    Returns:
        Estimated runtime in seconds
    """
    # Read input to get problem size
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        # First line is N (number of discrete ordinates)
        N = int(lines[0].strip())
        
        # Rough estimate: more ordinates = longer runtime
        # This is a placeholder - adjust based on actual benchmarks
        base_time = 1.0  # seconds
        time_per_ordinate = 0.5
        
        estimated = base_time + (N * time_per_ordinate)
        
        return estimated
    
    except Exception:
        # If we can't estimate, return a default
        return 60.0  # 1 minute default
