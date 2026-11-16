"""Diagnostic logging for the TUI.

Textual swallows exceptions into status widgets; writing them to
``outputs/logs/tui.log`` keeps a traceback available when a user reports a
failure.
"""

from __future__ import annotations

import logging

from utils.paths import LOGS_DIR

LOG_FILE = LOGS_DIR / "tui.log"

_HANDLER: logging.Handler | None = None


def configure_logging(level: int = logging.DEBUG) -> logging.Handler | None:
    """Attach one file handler to the TUI and Textual loggers."""
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
    for name in ("tui", "textual"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
    _HANDLER = handler
    return handler
