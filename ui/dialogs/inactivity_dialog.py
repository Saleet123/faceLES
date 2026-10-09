from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from config import settings, theme
from ui.widgets.modal import CenteredModal
from ui.widgets.primary_button import PrimaryButton


class InactivityDialog(CenteredModal):
    cancelled = Signal()
    timed_out = Signal()

    def __init__(
        self,
        reason: str,
        seconds: int | None = None,
        parent=None,
        *,
        allow_input: bool = False,
    ):
        super().__init__(parent, width=420, title="Idle detected")
        self._seconds = seconds or settings.COUNTDOWN_SECONDS
        self._active = True
        self._allow_input = allow_input
        self.reason = reason
        if allow_input:
            self.add_subtitle("No camera available. Move the mouse or press a key to cancel.")
        else:
            self.add_subtitle("Show your face in the camera to cancel. Mouse movement will not stop this.")

        self.timer_label = QLabel(f"{self._seconds}s")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet(
            f"color:{theme.PRIMARY}; font-size:44px; font-weight:800; background:transparent; padding:10px 0;"
        )
        self.body().addWidget(self.timer_label)

        self.face_status: QLabel | None = None
        if allow_input:
            cancel = PrimaryButton("I'm here — cancel", kind="primary")
            cancel.clicked.connect(self._cancel)
            self.add_actions(cancel)
        else:
            hint = QFrame()
            hint.setObjectName("faceCancelHint")
            hint.setStyleSheet(
                f"""
                QFrame#faceCancelHint {{
                    background: {theme.SOFT};
                    border: 1px solid {theme.BORDER};
                    border-radius: 12px;
                }}
                """
            )
            col = QVBoxLayout(hint)
            col.setContentsMargins(14, 12, 14, 12)
            col.setSpacing(4)
            title = QLabel("Show face to cancel")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet(
                f"color:{theme.PRIMARY}; font-size:14px; font-weight:800; background:transparent;"
            )
            self.face_status = QLabel("Waiting for your face…")
            self.face_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.face_status.setWordWrap(True)
            self.face_status.setStyleSheet(
                f"color:{theme.MUTED}; font-size:12px; background:transparent;"
            )
            col.addWidget(title)
            col.addWidget(self.face_status)
            self.body().addWidget(hint)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def set_face_status(self, *, has_face: bool, recognized: bool) -> None:
        if self.face_status is None or not self._active:
            return
        if recognized:
            self.face_status.setText("Face matched — cancelling…")
            self.face_status.setStyleSheet(
                f"color:{theme.SUCCESS}; font-size:12px; font-weight:700; background:transparent;"
            )
        elif has_face:
            self.face_status.setText("Face seen — look straight at the camera")
            self.face_status.setStyleSheet(
                f"color:{theme.ORANGE}; font-size:12px; font-weight:600; background:transparent;"
            )
        else:
            self.face_status.setText("Waiting for your face…")
            self.face_status.setStyleSheet(
                f"color:{theme.MUTED}; font-size:12px; background:transparent;"
            )

    def _tick(self) -> None:
        if not self._active:
            return
        self._seconds -= 1
        if self._seconds > 0:
            self.timer_label.setText(f"{self._seconds}s")
        else:
            self._active = False
            self._timer.stop()
            self.timed_out.emit()
            self.accept()

    def _cancel(self) -> None:
        self._active = False
        self._timer.stop()
        self.cancelled.emit()
        self.reject()

    def note_activity(self) -> None:
        if self._allow_input and self._active:
            self._cancel()

    def cancel_for_face(self) -> None:
        if self._active:
            self._cancel()


class AutoBreakDialog(CenteredModal):
    ended = Signal()

    def __init__(self, reason: str, start_time: datetime, parent=None):
        super().__init__(parent, width=380, title="Auto break")
        self._start = start_time
        display = "Idle Sitting" if reason == "Inactivity Only" else reason
        self.add_subtitle(display or "Auto")

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet(
            f"color:{theme.PRIMARY}; font-size:40px; font-weight:800; background:transparent; padding:12px 0;"
        )
        self.body().addWidget(self.timer_label)

        end = PrimaryButton("End break", kind="danger")
        end.clicked.connect(self._end)
        self.add_actions(end)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._update)
        self._tick.start(250)
        self._update()

    def _update(self) -> None:
        elapsed = datetime.now() - self._start
        self.timer_label.setText(str(elapsed).split(".")[0])

    def _end(self) -> None:
        self._tick.stop()
        self.ended.emit()
        self.accept()
