#!/usr/bin/env python3
"""Main entry point for NTS Automation System - CLI Interface."""

import sys
from utils.logger import setup_logging, get_logger
from utils.paths import ensure_directories, get_missing_solvers


def check_prerequisites():
    """
    Check system prerequisites before starting.
    
    Returns:
        bool: True if all prerequisites are met, False otherwise
    """
    logger = get_logger()
    
    # Ensure directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {str(e)}")
        return False
    
    # Check for missing solvers
    missing = get_missing_solvers()
    if missing:
        logger.warning(f"Missing solver binaries: {', '.join(missing)}")
    
    return True


def main():
    """Main entry point for CLI."""
    
    # Setup logging first (less verbose)
    import logging
    setup_logging(console_level=logging.WARNING)
    logger = get_logger()
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            logger.error("Prerequisites check failed")
            return 1
        
        # Run CLI
        from cli.commands import main as cli_main
        return cli_main()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\nUnexpected error: {str(e)}")
        print("Check the log file for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
