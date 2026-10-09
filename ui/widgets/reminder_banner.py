"""Non-blocking 1-minute warning — cancel auto-break without the 10s modal."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from config import theme
from ui.widgets.primary_button import PrimaryButton


class ReminderBanner(QFrame):
    stay_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reminderBanner")
        self.setFixedHeight(46)
        self.setStyleSheet(
            f"""
            QFrame#reminderBanner {{
                background: #FFF8E8;
                border: none;
                border-bottom: 1px solid #F0E0B8;
            }}
            QFrame#reminderBanner QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 6, 18, 6)
        row.setSpacing(10)

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{theme.ORANGE}; font-size:12px; background:transparent;")
        row.addWidget(self.dot)

        self.message = QLabel("Auto-break in 1:00")
        self.message.setStyleSheet(
            f"color:{theme.NAVY}; font-size:13px; font-weight:600; background:transparent;"
        )
        row.addWidget(self.message, 1)

        self.stay_btn = PrimaryButton("I'm here", kind="primary")
        self.stay_btn.setMinimumHeight(32)
        self.stay_btn.setMinimumWidth(96)
        self.stay_btn.clicked.connect(self.stay_requested.emit)
        row.addWidget(self.stay_btn)

        self.face_hint = QLabel("Show face to cancel")
        self.face_hint.setStyleSheet(
            f"""
            color: white;
            background: {theme.PRIMARY};
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 700;
            """
        )
        self.face_hint.hide()
        row.addWidget(self.face_hint)
        self.hide()

    def show_warning(
        self,
        remaining_seconds: float,
        *,
        away: bool,
        camera_available: bool = True,
    ) -> None:
        total = max(0, int(remaining_seconds))
        clock = f"{total // 60}:{total % 60:02d}"
        if not camera_available:
            self.message.setText(f"Auto-break in {clock}. Move the mouse or click I'm here.")
            self.stay_btn.show()
            self.face_hint.hide()
        elif away:
            self.message.setText(f"Off camera — auto-break in {clock}. Show your face to cancel.")
            self.stay_btn.hide()
            self.face_hint.show()
        else:
            self.message.setText(f"No activity — auto-break in {clock}. Show your face to cancel.")
            self.stay_btn.hide()
            self.face_hint.show()
        if not self.isVisible():
            self.show()

    def hide_warning(self) -> None:
        if self.isVisible():
            self.hide()
