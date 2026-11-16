"""Service layer for the TUI.

Modules in this package never import Textual.  They can be tested headlessly
and reused by the CLI.

Submodules are intentionally not imported here: importing ``tui.services``
must stay cheap.  Use ``from tui.services import plots`` (the import system
loads the submodule on demand).
"""

__all__ = [
    "config_store",
    "export",
    "plots",
    "results",
    "runner",
    "sweeps",
    "terminal",
]
