"""Widgets used by the 2D TUI."""

from .bc_table import BCTable
from .domain_view import DomainMap
from .image_preview import ImagePreview
from .matrix_editor import MatrixEditor
from .row_table import Column, RegionTable, RowTable, ZoneTable

__all__ = [
    "BCTable",
    "Column",
    "DomainMap",
    "ImagePreview",
    "MatrixEditor",
    "RegionTable",
    "RowTable",
    "ZoneTable",
]
