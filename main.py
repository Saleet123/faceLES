#!/usr/bin/env python3
"""FaceLES PySide6 entry point."""
from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path when launched as a script.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# OpenCV's wheel ships its own Qt plugins; they conflict with PySide6's xcb plugin.
# Clear any cv2-injected plugin paths before Qt initializes.
for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
    value = os.environ.get(key, "")
    if "cv2" in value or "opencv" in value.lower():
        os.environ.pop(key, None)

import PySide6
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from config import settings

os.chdir(settings.DATA_DIR)

_plugin_candidates = [
    os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins"),
    os.path.join(os.path.dirname(PySide6.__file__), "Qt6", "plugins"),
    os.path.join(settings.BUNDLE_DIR, "PySide6", "Qt", "plugins"),
    os.path.join(settings.BUNDLE_DIR, "PySide6", "Qt6", "plugins"),
]
_pyside_plugins = next((path for path in _plugin_candidates if os.path.isdir(path)), "")
if _pyside_plugins:
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _pyside_plugins
    QCoreApplication.setLibraryPaths([_pyside_plugins])
from ui.main_window import MainWindow
from ui.widgets.icons import app_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FaceLES")
    app.setOrganizationName("FaceLES")
    app.setDesktopFileName("FaceLES")
    icon = app_icon()
    app.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    screen = app.primaryScreen()
    if screen is not None:
        geo = screen.availableGeometry()
        window.setGeometry(
            max(0, (geo.width() - settings.WINDOW_W) // 2),
            max(0, (geo.height() - settings.WINDOW_H) // 3),
            settings.WINDOW_W,
            settings.WINDOW_H,
        )
    else:
        window.resize(settings.WINDOW_W, settings.WINDOW_H)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
