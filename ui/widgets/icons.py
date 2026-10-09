"""Load SVG icons as QIcons / QPixmaps."""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from config import settings

_ICON_DIR = os.path.join(settings.BUNDLE_DIR, "assets", "icons")


def svg_pixmap(name: str, size: int = 18, color: str | None = None) -> QPixmap:
    path = os.path.join(_ICON_DIR, name if name.endswith(".svg") else f"{name}.svg")
    renderer = QSvgRenderer(path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def svg_icon(name: str, size: int = 18) -> QIcon:
    return QIcon(svg_pixmap(name, size))


def app_icon() -> QIcon:
    """Multi-resolution FaceLES application icon for the window/taskbar."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        png = os.path.join(_ICON_DIR, f"app-{size}.png")
        if os.path.isfile(png):
            icon.addFile(png, QSize(size, size))
    if icon.isNull():
        fallback = os.path.join(_ICON_DIR, "app.png")
        if os.path.isfile(fallback):
            icon.addFile(fallback)
        else:
            icon = svg_icon("app", 64)
    return icon
