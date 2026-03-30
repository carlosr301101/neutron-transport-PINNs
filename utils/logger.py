"""Logging configuration and utilities for NTS automation."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class NTSLogger:
    """Centralized logging for NTS automation system."""
    
    _instance: Optional['NTSLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.logger = logging.getLogger('nts_automation')
            self.logger.setLevel(logging.DEBUG)
            self._initialized = True
    
    def setup(self, log_dir: str = "outputs/logs", console_level: int = logging.INFO):
        """
        Setup logging with file and console handlers.
        
        Args:
            log_dir: Directory for log files
            console_level: Logging level for console output
        """
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_path / f"nts_automation_{timestamp}.log"
        
        # File handler - detailed logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler - user-facing logs
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging initialized. Log file: {log_file}")
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance."""
        return self.logger


def get_logger() -> logging.Logger:
    """
    Get the NTS automation logger.
    
    Returns:
        Logger instance
    """
    nts_logger = NTSLogger()
    return nts_logger.get_logger()


def setup_logging(log_dir: str = "outputs/logs", console_level: int = logging.INFO):
    """
    Setup logging system.
    
    Args:
        log_dir: Directory for log files
        console_level: Logging level for console (DEBUG, INFO, WARNING, ERROR)
    """
    nts_logger = NTSLogger()
    nts_logger.setup(log_dir, console_level)


class SimulationLogger:
    """Logger for individual simulation runs with metrics tracking."""
    
    def __init__(self, simulation_id: str, log_dir: str = "outputs/logs"):
        """
        Initialize simulation logger.
        
        Args:
            simulation_id: Unique identifier for this simulation
            log_dir: Directory for simulation logs
        """
        self.simulation_id = simulation_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create simulation-specific log file
        self.log_file = self.log_dir / f"simulation_{simulation_id}.log"
        
        # Setup simulation logger
        self.logger = logging.getLogger(f'nts_simulation_{simulation_id}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Metrics
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'duration': None,
            'solver': None,
            'input_file': None,
            'output_file': None,
            'status': 'initialized'
        }
    
    def start(self, solver: str, input_file: str, output_file: str):
        """Log simulation start."""
        self.metrics['start_time'] = datetime.now()
        self.metrics['solver'] = solver
        self.metrics['input_file'] = input_file
        self.metrics['output_file'] = output_file
        self.metrics['status'] = 'running'
        
        self.logger.info("=" * 60)
        self.logger.info(f"Simulation {self.simulation_id} started")
        self.logger.info(f"Solver: {solver}")
        self.logger.info(f"Input: {input_file}")
        self.logger.info(f"Output: {output_file}")
        self.logger.info("=" * 60)
    
    def end(self, status: str, exit_code: int = 0):
        """Log simulation end."""
        self.metrics['end_time'] = datetime.now()
        self.metrics['status'] = status
        
        if self.metrics['start_time']:
            duration = self.metrics['end_time'] - self.metrics['start_time']
            self.metrics['duration'] = duration.total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info(f"Simulation {self.simulation_id} {status}")
        if self.metrics['duration']:
            self.logger.info(f"Duration: {self.metrics['duration']:.2f} seconds")
        self.logger.info(f"Exit code: {exit_code}")
        self.logger.info("=" * 60)
    
    def log_stdout(self, line: str):
        """Log stdout from solver."""
        self.logger.debug(f"STDOUT: {line.rstrip()}")
    
    def log_stderr(self, line: str):
        """Log stderr from solver."""
        self.logger.warning(f"STDERR: {line.rstrip()}")
    
    def get_metrics(self) -> dict:
        """Get simulation metrics."""
        return self.metrics.copy()
