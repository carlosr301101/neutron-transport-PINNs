"""Path helpers shared by the TUI service layer.

Numbering lives here so configs, results and plots cannot hand out a name that
already exists.
"""

from __future__ import annotations

import re
from pathlib import Path

from utils.paths import PLOTS_DIR, WORK_ROOT

PLOT_NAMES = {
    "scalar": "scalar_flux.png",
    "angular": "angular_flux.png",
    "k-history": "k_history.png",
    "scs": "scs_flux.png",
}


def resolve_path(text: str | Path, base: Path = WORK_ROOT) -> Path:
    """Anchor a user-supplied path to *base* when it is relative."""
    path = Path(text).expanduser()
    return path if path.is_absolute() else Path(base) / path


def numbered_path(
    directory: Path,
    prefix: str,
    suffix: str = ".json",
    width: int = 3,
) -> Path:
    """Next free ``<prefix><number><suffix>`` inside *directory*.

    The index comes from the highest number already present (not from the last
    name in alphabetical order) and the result is guaranteed not to exist.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+){re.escape(suffix)}$")

    highest = 0
    for path in directory.glob(f"{prefix}*{suffix}"):
        match = pattern.match(path.name)
        if match is not None:
            highest = max(highest, int(match.group(1)))

    index = highest + 1
    while True:
        candidate = directory / f"{prefix}{index:0{width}d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def unique_path(path: Path | str) -> Path:
    """Return *path* or a numbered sibling if it already exists."""
    path = Path(path)
    if not path.exists():
        return path
    for index in range(1, 10_000):
        candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot find a free name for {path}")


def default_plot_path(kind: str) -> Path:
    """Collision-free default PNG path for one plot kind."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    return unique_path(PLOTS_DIR / PLOT_NAMES.get(kind, f"{kind}.png"))
