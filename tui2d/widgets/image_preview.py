"""Optional inline image preview for 2D heatmaps."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Container, VerticalScroll
from textual.widgets import Static

from tui.services.terminal import detect_image_protocol, textual_image_available


class ImagePreview(VerticalScroll):
    """Show a generated PNG inline when the terminal supports it."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.path: Path | None = None

    def compose(self):
        yield Container(id="tui2d-preview-body")
        yield Static(
            "Generate a heatmap to see the preview.",
            id="tui2d-preview-status",
            classes="muted",
        )

    def show(self, path: Path | str) -> None:
        """Display *path*, or a fallback message when inline is unavailable."""
        self.path = Path(path)
        body = self.query_one("#tui2d-preview-body", Container)
        status = self.query_one("#tui2d-preview-status", Static)
        body.remove_children()

        protocol = detect_image_protocol()
        if protocol and textual_image_available():
            try:
                image = self._make_image(self.path)
                body.mount(image)
                status.update(f"Inline preview ({protocol}). {self.path}")
                return
            except Exception:
                self.log.debug("inline image failed", exc_info=True)

        status.update(
            "Inline preview not supported by this terminal.\n"
            f"PNG saved: {self.path}\nUse the Open button."
        )

    @staticmethod
    def _make_image(path: Path):
        from textual_image.widget import Image  # type: ignore[import-not-found]

        return Image(str(path))
