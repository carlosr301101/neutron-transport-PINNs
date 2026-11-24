"""Diagnostic logging for the 2D TUI."""

from __future__ import annotations

import logging

from utils.paths import LOGS_DIR

LOG_FILE = LOGS_DIR / "tui2d.log"

_HANDLER: logging.Handler | None = None


def configure_logging(level: int = logging.DEBUG) -> logging.Handler | None:
    """Attach one file handler to the 2D TUI and Textual loggers."""
    global _HANDLER
    if _HANDLER is not None:
        return _HANDLER

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    except OSError:  # read-only checkout: stay silent
        return None

    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    for name in ("tui2d", "textual"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
    _HANDLER = handler
    return handler
