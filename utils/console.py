"""Console encoding helpers for the command-line entry points."""

from __future__ import annotations

import contextlib
import sys


def configure_stdio() -> None:
    """Avoid ``UnicodeEncodeError`` on legacy Windows code pages.

    The CLIs print symbols such as ``✓`` and ``→``.  Windows consoles often
    use cp1252, which cannot encode them and makes ``print`` raise.  Keeping
    the stream's encoding but replacing unencodable characters is enough for
    the CLIs, their tests and CI logs; ASCII text is unaffected.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        with contextlib.suppress(AttributeError, OSError, ValueError):
            stream.reconfigure(errors="replace")
