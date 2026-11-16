"""Optional inline image preview with a text fallback."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Container, VerticalScroll
from textual.widgets import Static

from ..services.terminal import (
    detect_image_protocol,
    textual_image_available,
)


class ImagePreview(VerticalScroll):
    """Show a generated PNG inline when the terminal and package support it."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.path: Path | None = None

    def compose(self):
        yield Container(id="preview-body")
        yield Static(
            "Generate a plot to see the preview.",
            id="preview-status",
            classes="muted",
        )

    def show(self, path: Path | str) -> None:
        """Display *path*, or a fallback message when inline is unavailable."""
        self.path = Path(path)
        body = self.query_one("#preview-body", Container)
        status = self.query_one("#preview-status", Static)
        body.remove_children()

        protocol = detect_image_protocol()
        if protocol and textual_image_available():
            try:
                image = self._make_image(self.path)
                body.mount(image)
                status.update(f"Inline preview ({protocol}). {self.path}")
                return
            except Exception:  # noqa: BLE001 - fall back to text
                pass

        status.update(
            "Inline preview not supported by this terminal.\n"
            f"PNG saved: {self.path}\nUse the Open button."
        )

    @staticmethod
    def _make_image(path: Path):
        from textual_image.widget import Image  # type: ignore[import-not-found]

        return Image(str(path))
