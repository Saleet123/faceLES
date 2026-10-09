"""Non-blocking on-break bar — dashboard stays usable while a break runs."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from config import theme
from ui.widgets.primary_button import PrimaryButton


class BreakBanner(QFrame):
    """Slim pill/bar showing break type, live duration, and End break."""

    end_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("breakBanner")
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"""
            QFrame#breakBanner {{
                background: #FFF6ED;
                border: none;
                border-bottom: 1px solid #F0DCC8;
            }}
            """
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 6, 18, 6)
        row.setSpacing(12)

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{theme.ORANGE}; font-size:12px; background:transparent;")
        row.addWidget(self.dot)

        self.reason_label = QLabel("On break")
        self.reason_label.setStyleSheet(
            f"color:{theme.NAVY}; font-size:13px; font-weight:700; background:transparent;"
        )
        row.addWidget(self.reason_label)

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet(
            f"color:{theme.ORANGE}; font-size:15px; font-weight:800; background:transparent;"
        )
        row.addWidget(self.timer_label)

        self.tip = QLabel("Dashboard stays available — end when you're back.")
        self.tip.setStyleSheet(f"color:{theme.MUTED}; font-size:12px; background:transparent;")
        self.tip.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.tip, 1)

        self.end_btn = PrimaryButton("End break", kind="danger")
        self.end_btn.setMinimumHeight(34)
        self.end_btn.setMinimumWidth(110)
        self.end_btn.clicked.connect(self.end_requested.emit)
        row.addWidget(self.end_btn)

        self._start: datetime | None = None
        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._update)
        self.hide()

    def start(self, reason: str, start_time: datetime, *, face_resume: bool = False) -> None:
        display = "Idle Sitting" if reason == "Inactivity Only" else reason
        self.reason_label.setText(f"On break · {display}")
        if face_resume:
            self.tip.setText("Show your face to end this auto-break.")
        else:
            self.tip.setText("Dashboard stays available — end when you're back.")
        self._start = start_time
        self._update()
        self._tick.start()
        self.show()

    def stop(self) -> None:
        self._tick.stop()
        self._start = None
        self.hide()

    def _update(self) -> None:
        if self._start is None:
            return
        elapsed = datetime.now() - self._start
        self.timer_label.setText(str(elapsed).split(".")[0])
