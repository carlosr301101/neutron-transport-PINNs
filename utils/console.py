"""Console output helpers with ASCII fallbacks for legacy Windows code pages.

Windows PowerShell sessions often run with a legacy code page (``cp1252`` or
``cp850``) that cannot encode symbols such as ``✓`` (U+2713).  Rich writes
directly to ``stdout``, so a checkmark makes it raise ``UnicodeEncodeError``.

On Windows the CLI therefore prints ASCII markers by default (``OK``, ``X``,
``-``) and tells Rich to use ASCII tables and spinners.  Set ``NTS_UNICODE=1``
to keep the Unicode glyphs, or ``NTS_ASCII=1`` to force ASCII anywhere.
"""

from __future__ import annotations

import os
import sys
from typing import IO, Any

from rich.console import Console

_TRUE_VALUES = {"1", "true", "yes", "on"}

_ASCII_REPLACEMENTS = {
    "✓": "OK",
    "✗": "X",
    "•": "-",
    "→": "->",
    "←": "<-",
    "↔": "<->",
    "Δ": "Delta",
    "Σ": "Sigma",
    "σ": "sigma",
    "μ": "mu",
    "ω": "omega",
    "θ": "theta",
    "ψ": "psi",
    "φ": "phi",
    "λ": "lambda",
    "ν": "nu",
    "≈": "~=",
    "≥": ">=",
    "≤": "<=",
    "≠": "!=",
    "±": "+/-",
    "∞": "inf",
    "√": "sqrt",
    "×": "x",
    "·": "-",
    "…": "...",
    "—": "-",
    "–": "-",
    "⁺": "+",
    "⁻": "-",
    "²": "^2",
    "³": "^3",
}
_ASCII_TABLE = str.maketrans(_ASCII_REPLACEMENTS)


def _flag(name: str) -> bool:
    """Return True when an environment flag is set to a truthy value."""
    return os.environ.get(name, "").strip().lower() in _TRUE_VALUES


def use_ascii() -> bool:
    """Return True when console output should avoid non-ASCII characters.

    ``NTS_UNICODE=1`` and ``NTS_ASCII=1`` override the platform default.
    Windows defaults to ASCII because its legacy code pages cannot encode the
    symbols used by the CLI.  Elsewhere the stdout encoding decides.
    """
    if _flag("NTS_UNICODE"):
        return False
    if _flag("NTS_ASCII"):
        return True
    if sys.platform == "win32":
        return True
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    return bool(encoding) and not encoding.startswith("utf")


def ascii_text(text: str) -> str:
    """Replace console glyphs with their ASCII equivalents."""
    return text.translate(_ASCII_TABLE)


def _stream_uses_ascii(stream: IO[str] | None) -> bool:
    """Return True when *stream* cannot be trusted with Unicode output."""
    if use_ascii():
        return True
    encoding = (getattr(stream, "encoding", None) or "").lower()
    return bool(encoding) and not encoding.startswith("utf")


def console_uses_ascii(console: Console) -> bool:
    """Return True when *console* should use ASCII text and decorations.

    A console bound to a non-UTF stream (for example
    ``PYTHONIOENCODING=cp1252``) must stay in ASCII even on Linux, otherwise
    Rich's progress bar and table borders fail to encode.
    """
    if use_ascii():
        return True
    encoding = (console.encoding or "").lower()
    return bool(encoding) and not encoding.startswith("utf")


def _reconfigure(stream: IO[str], **kwargs: Any) -> None:
    """Best-effort ``TextIOWrapper.reconfigure`` that ignores closed streams."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(**kwargs)
    except (AttributeError, OSError, ValueError):
        pass


def configure_stdio() -> None:
    """Make stdout/stderr tolerant of legacy Windows code pages.

    On Windows the streams keep their encoding but replace unencodable
    characters instead of raising.  With ``NTS_UNICODE=1`` they are switched
    to UTF-8 so the Unicode glyphs can be written.
    """
    if sys.platform != "win32":
        return
    streams = [stream for stream in (sys.stdout, sys.stderr) if stream is not None]
    if _flag("NTS_UNICODE"):
        for stream in streams:
            _reconfigure(stream, encoding="utf-8", errors="replace")
    else:
        for stream in streams:
            _reconfigure(stream, errors="replace")


class SafeConsole(Console):
    """Rich console that prints ASCII markers when the terminal requires it."""

    def print(self, *objects: Any, **kwargs: Any) -> None:
        if console_uses_ascii(self):
            objects = tuple(
                ascii_text(obj) if isinstance(obj, str) else obj for obj in objects
            )
        super().print(*objects, **kwargs)


_console: SafeConsole | None = None
_configured = False


def configure_console() -> None:
    """Configure stdio once, before the first console write."""
    global _configured
    if _configured:
        return
    configure_stdio()
    _configured = True


def get_console() -> SafeConsole:
    """Return the shared console, configuring stdio on first use."""
    global _console
    configure_console()
    if _console is None:
        _console = SafeConsole()
    return _console


def emit(*args: Any, **kwargs: Any) -> None:
    """``print`` with the same ASCII fallback used by the Rich console."""
    configure_console()
    stream = kwargs.get("file")
    if _stream_uses_ascii(sys.stdout if stream is None else stream):
        args = tuple(
            ascii_text(arg) if isinstance(arg, str) else arg for arg in args
        )
    print(*args, **kwargs)
