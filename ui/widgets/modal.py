"""Centered in-app modals drawn inside the FaceLES main window (not separate OS windows)."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from config import theme


def _overlay_host(parent: QWidget | None) -> QWidget | None:
    """Prefer the main window's central widget so the veil covers the UI."""
    if parent is None:
        return None
    window = parent.window()
    if isinstance(window, QMainWindow) and window.centralWidget() is not None:
        return window.centralWidget()
    return window


class CenteredModal(QDialog):
    """
    Full-window overlay card centered over the FaceLES main window.

    Implemented as a child widget (not a top-level OS window) so Wayland/X11
    cannot place it beside the app.
    """

    def __init__(self, parent=None, *, width: int = 420, title: str = ""):
        host = _overlay_host(parent)
        super().__init__(host)
        self._host: QWidget | None = host
        self._preferred_width = width

        # Child of the main window — not a floating top-level dialog.
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setObjectName("centeredModal")
        self.setStyleSheet("QDialog#centeredModal { background: transparent; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        center_col = QVBoxLayout()
        center_col.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("modalCard")
        self.card.setFixedWidth(width)
        self.card.setStyleSheet(
            f"""
            QFrame#modalCard {{
                background: {theme.CARD};
                border: 1px solid {theme.BORDER};
                border-radius: 16px;
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(16, 35, 71, 80))
        self.card.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(28, 24, 28, 24)
        self.card_layout.setSpacing(12)

        if title:
            heading = QLabel(title)
            heading.setObjectName("modalTitle")
            heading.setStyleSheet(
                f"color:{theme.NAVY}; font-size:20px; font-weight:800; background:transparent;"
            )
            self.card_layout.addWidget(heading)

        center_col.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        center_col.addStretch(1)
        center_row.addLayout(center_col)
        center_row.addStretch(1)
        root.addLayout(center_row)

        if self._host is not None:
            self._host.installEventFilter(self)
            self._sync_to_host()

    def add_subtitle(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color:{theme.MUTED}; font-size:13px; background:transparent;")
        self.card_layout.addWidget(label)
        return label

    def body(self) -> QVBoxLayout:
        return self.card_layout

    def add_actions(self, *buttons, stretch_before: bool = True) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        if stretch_before:
            row.addStretch(1)
        for btn in buttons:
            row.addWidget(btn)
        if not stretch_before:
            row.addStretch(1)
        self.card_layout.addSpacing(6)
        self.card_layout.addLayout(row)
        return row

    def _sync_to_host(self) -> None:
        if self._host is None:
            return
        self.setGeometry(self._host.rect())
        self.raise_()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(16, 35, 71, 140))
        super().paintEvent(event)

    def showEvent(self, event):  # noqa: N802
        self._sync_to_host()
        self.raise_()
        self.activateWindow()
        super().showEvent(event)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._host and event.type() == QEvent.Type.Resize:
            self._sync_to_host()
        return super().eventFilter(obj, event)

    def done(self, result: int) -> None:  # noqa: N802
        if self._host is not None:
            self._host.removeEventFilter(self)
        super().done(result)

    def closeEvent(self, event):  # noqa: N802
        if self._host is not None:
            self._host.removeEventFilter(self)
        super().closeEvent(event)


class AlertModal(CenteredModal):
    """Simple confirm / info card used instead of native QMessageBox."""

    def __init__(self, parent, title: str, message: str, *, kind: str = "info"):
        super().__init__(parent, width=400, title=title)
        self.add_subtitle(message)
        from ui.widgets.primary_button import PrimaryButton

        ok = PrimaryButton("OK", kind="primary" if kind != "danger" else "danger")
        ok.clicked.connect(self.accept)
        self.add_actions(ok)

    @staticmethod
    def info(parent, title: str, message: str) -> int:
        return AlertModal(parent, title, message, kind="info").exec()

    @staticmethod
    def error(parent, title: str, message: str) -> int:
        return AlertModal(parent, title, message, kind="danger").exec()

    @staticmethod
    def confirm(parent, title: str, message: str) -> bool:
        dlg = CenteredModal(parent, width=400, title=title)
        dlg.add_subtitle(message)
        from ui.widgets.primary_button import PrimaryButton

        cancel = PrimaryButton("Cancel", kind="ghost")
        cancel.clicked.connect(dlg.reject)
        yes = PrimaryButton("Yes", kind="danger")
        yes.clicked.connect(dlg.accept)
        dlg.add_actions(cancel, yes)
        return dlg.exec() == QDialog.DialogCode.Accepted
