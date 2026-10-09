from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QRadioButton, QVBoxLayout

from config import settings, theme
from ui.widgets.modal import CenteredModal
from ui.widgets.primary_button import PrimaryButton


class _BreakOptionRow(QFrame):
    def __init__(self, radio: QRadioButton, parent=None):
        super().__init__(parent)
        self._radio = radio
        self.setObjectName("breakOption")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QFrame#breakOption {{
                background: {theme.SOFT};
                border: 1px solid {theme.BORDER};
                border-radius: 10px;
            }}
            QFrame#breakOption:hover {{
                border: 1px solid {theme.PRIMARY};
                background: #e4f0ff;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(radio, 1)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._radio.setChecked(True)
        super().mousePressEvent(event)


class BreakSelectDialog(CenteredModal):
    selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, width=420, title="Start a break")
        self.add_subtitle("Choose why you're stepping away.")

        self.group = QButtonGroup(self)
        options = QVBoxLayout()
        options.setSpacing(8)
        for i, option in enumerate(settings.MANUAL_BREAK_OPTIONS):
            radio = QRadioButton(option)
            radio.setStyleSheet(
                f"""
                QRadioButton {{
                    font-size: 14px;
                    font-weight: 600;
                    color: {theme.NAVY};
                    spacing: 10px;
                    background: transparent;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 2px solid {theme.BORDER};
                    background: white;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid {theme.PRIMARY};
                    background: {theme.PRIMARY};
                }}
                """
            )
            self.group.addButton(radio, i)
            options.addWidget(_BreakOptionRow(radio))
            if i == 0:
                radio.setChecked(True)

        self.body().addLayout(options)

        cancel = PrimaryButton("Cancel", kind="ghost")
        cancel.clicked.connect(self.reject)
        start = PrimaryButton("Start break", kind="primary")
        start.clicked.connect(self._accept)
        self.add_actions(cancel, start)

    def _accept(self) -> None:
        btn = self.group.checkedButton()
        if not btn:
            return
        self.selected.emit(btn.text())
        self.accept()


class BreakTimerDialog(CenteredModal):
    ended = Signal()

    def __init__(self, reason: str, start_time: datetime, parent=None):
        super().__init__(parent, width=380, title=f"{reason} break")
        self._start = start_time
        self.add_subtitle("Timer is running — return when you're back.")

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
