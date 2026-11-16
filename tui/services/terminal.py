"""Terminal capability detection for optional inline image preview."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def detect_image_protocol() -> str | None:
    """Return ``kitty``, ``sixel`` or ``iterm2`` when the terminal advertises it."""
    if os.environ.get("KITTY_WINDOW_ID"):
        return "kitty"
    if os.environ.get("WEZTERM_PANE"):
        return "iterm2"

    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if "iterm" in term_program:
        return "iterm2"
    if "wezterm" in term_program:
        return "iterm2"

    term = os.environ.get("TERM", "").lower()
    if "sixel" in term:
        return "sixel"
    if "kitty" in term:
        return "kitty"
    return None


def textual_image_available() -> bool:
    """True when the optional ``textual-image`` package can be imported."""
    return importlib.util.find_spec("textual_image") is not None


def inline_available() -> bool:
    return detect_image_protocol() is not None and textual_image_available()


def open_path(path: Path | str) -> None:
    """Open a file with the desktop default application."""
    path = str(path)
    if sys.platform.startswith("darwin"):
        command = ["open", path]
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    else:
        command = ["xdg-open", path]
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
