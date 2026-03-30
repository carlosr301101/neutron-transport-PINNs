"""Parallel execution of multiple NTS solvers."""

from multiprocessing import Pool, cpu_count
from typing import List, Tuple, Callable, Optional, Any
import time
from pathlib import Path

from execution.runner import run_solver, SolverResult
from utils.logger import get_logger


class ParallelExecutionResult:
    """Result of parallel execution."""
    
    def __init__(self):
        self.tasks: List[Tuple] = []
        self.results: List[SolverResult] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_duration: Optional[float] = None
    
    def add_result(self, task: Tuple, result: SolverResult):
        """Add a task result."""
        self.tasks.append(task)
        self.results.append(result)
    
    def finalize(self):
        """Finalize timing information."""
        if self.start_time and self.end_time:
            self.total_duration = self.end_time - self.start_time
    
    @property
    def success_count(self) -> int:
        """Count of successful executions."""
        return sum(1 for r in self.results if r.success)
    
    @property
    def failure_count(self) -> int:
        """Count of failed executions."""
        return sum(1 for r in self.results if not r.success)
    
    @property
    def total_count(self) -> int:
        """Total number of tasks."""
        return len(self.results)
    
    def get_summary(self) -> str:
        """Get execution summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("Parallel Execution Summary")
        lines.append("=" * 60)
        lines.append(f"Total tasks: {self.total_count}")
        lines.append(f"Successful: {self.success_count}")
        lines.append(f"Failed: {self.failure_count}")
        
        if self.total_duration:
            lines.append(f"Total duration: {self.total_duration:.2f} seconds")
            avg_time = self.total_duration / self.total_count if self.total_count > 0 else 0
            lines.append(f"Average time per task: {avg_time:.2f} seconds")
        
        # Individual task results
        lines.append("\nIndividual Results:")
        for i, (task, result) in enumerate(zip(self.tasks, self.results), 1):
            executable, input_file, output_file = task
            status = "✓" if result.success else "✗"
            lines.append(f"  {i}. {status} {Path(input_file).name} -> {Path(output_file).name} ({result.duration:.2f}s)")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def _task_wrapper(args: Tuple) -> Tuple[Tuple, SolverResult]:
    """
    Wrapper function for parallel task execution.
    
    Args:
        args: Tuple of (executable, input_file, output_file, timeout, simulation_id)
        
    Returns:
        Tuple of (original_task, SolverResult)
    """
    executable, input_file, output_file = args[:3]
    timeout = args[3] if len(args) > 3 else 3600
    simulation_id = args[4] if len(args) > 4 else None
    
    # Run solver (output is already JSON)
    result = run_solver(executable, input_file, output_file, timeout, simulation_id)
    
    return ((executable, input_file, output_file), result)


def run_parallel(
    tasks: List[Tuple[str, str, str]],
    nproc: Optional[int] = None,
    timeout: int = 3600,
    callback: Optional[Callable[[int, int], None]] = None
) -> ParallelExecutionResult:
    """
    Run multiple solver tasks in parallel.
    
    Args:
        tasks: List of (executable, input_file, output_file) tuples
        nproc: Number of processes to use (default: CPU count)
        timeout: Timeout for each task in seconds
        callback: Optional callback function(completed, total) for progress updates
        
    Returns:
        ParallelExecutionResult with all task results
    """
    logger = get_logger()
    
    if nproc is None:
        nproc = cpu_count()
    
    logger.info(f"Starting parallel execution of {len(tasks)} tasks with {nproc} processes")
    
    # Prepare task arguments
    task_args = [(exe, inp, out, timeout, f"{int(time.time())}_{i}") 
                 for i, (exe, inp, out) in enumerate(tasks)]
    
    # Initialize result
    exec_result = ParallelExecutionResult()
    exec_result.start_time = time.time()
    
    # Run tasks in parallel
    try:
        with Pool(nproc) as pool:
            # Use imap_unordered for progress tracking
            completed = 0
            for task, result in pool.imap_unordered(_task_wrapper, task_args):
                exec_result.add_result(task, result)
                completed += 1
                
                # Progress callback
                if callback:
                    callback(completed, len(tasks))
                
                # Log progress
                status = "✓" if result.success else "✗"
                logger.info(f"[{completed}/{len(tasks)}] {status} {Path(task[1]).name} ({result.duration:.2f}s)")
    
    except Exception as e:
        logger.error(f"Error during parallel execution: {str(e)}")
    
    finally:
        exec_result.end_time = time.time()
        exec_result.finalize()
    
    logger.info(exec_result.get_summary())
    
    return exec_result


def run_parallel_simple(
    tasks: List[Tuple[str, str, str]],
    nproc: Optional[int] = None
) -> bool:
    """
    Simplified interface for parallel execution.
    
    Args:
        tasks: List of (executable, input_file, output_file) tuples
        nproc: Number of processes to use
        
    Returns:
        True if all tasks succeeded, False otherwise
    """
    result = run_parallel(tasks, nproc)
    return result.failure_count == 0


def run_batch(
    solver: str,
    input_files: List[str],
    output_dir: str,
    nproc: Optional[int] = None,
    output_prefix: str = "output"
) -> ParallelExecutionResult:
    """
    Run a batch of simulations with the same solver.
    
    Args:
        solver: Solver name or path
        input_files: List of input file paths
        output_dir: Directory for output files
        nproc: Number of processes
        output_prefix: Prefix for output filenames
        
    Returns:
        ParallelExecutionResult
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create tasks
    tasks = []
    for i, input_file in enumerate(input_files, 1):
        input_path = Path(input_file)
        output_file = output_path / f"{output_prefix}_{i:03d}.txt"
        tasks.append((solver, str(input_path), str(output_file)))
    
    return run_parallel(tasks, nproc)


def run_solver_comparison(
    solvers: List[str],
    input_file: str,
    output_dir: str,
    nproc: Optional[int] = None
) -> ParallelExecutionResult:
    """
    Run multiple solvers on the same input for comparison.
    
    Args:
        solvers: List of solver names
        input_file: Input file path
        output_dir: Directory for outputs
        nproc: Number of processes
        
    Returns:
        ParallelExecutionResult
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    input_name = Path(input_file).stem
    
    # Create tasks
    tasks = []
    for solver in solvers:
        output_file = output_path / f"{input_name}_{solver}.txt"
        tasks.append((solver, input_file, str(output_file)))
    
    return run_parallel(tasks, nproc)


def estimate_parallel_time(tasks: List[Tuple], nproc: int) -> float:
    """
    Estimate total execution time for parallel tasks.
    
    This is a rough estimate assuming equal distribution and no overhead.
    
    Args:
        tasks: List of tasks
        nproc: Number of processes
        
    Returns:
        Estimated time in seconds
    """
    # Rough estimate: assume each task takes 60 seconds
    # In practice, you'd want to estimate based on input size
    avg_task_time = 60.0
    
    # Parallel time = total_time / nproc
    total_sequential_time = len(tasks) * avg_task_time
    parallel_time = total_sequential_time / nproc
    
    return parallel_time
