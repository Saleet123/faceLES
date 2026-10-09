"""FaceLES shift-monitor dashboard matching the supplied design."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from datetime import datetime

from config import settings, theme
from ui.widgets.break_banner import BreakBanner
from ui.widgets.break_table import BreakLogTable
from ui.widgets.reminder_banner import ReminderBanner
from ui.widgets.camera_widget import CameraWidget
from ui.widgets.icons import svg_icon
from ui.widgets.primary_button import PrimaryButton
from ui.widgets.stat_card import StatCard
from ui.widgets.status_indicator import StatusIndicator


class DashboardHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(58)
        row = QHBoxLayout(self)
        row.setContentsMargins(22, 0, 18, 0)
        title = QLabel("FaceLES  |  Shift monitor")
        title.setStyleSheet("color:white; font-size:15px; font-weight:700;")
        row.addWidget(title)
        row.addStretch()
        self.status = StatusIndicator()
        row.addWidget(self.status)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(theme.DEEP))
        grad.setColorAt(0.55, QColor(theme.PRIMARY))
        grad.setColorAt(1.0, QColor(theme.BRIGHT))
        painter.fillRect(self.rect(), QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 22))
        # Keep the highlight off the status chip so the pill stays a single shape.
        painter.setClipRect(0, 0, max(0, self.width() - 168), self.height())
        path = QPainterPath()
        path.moveTo(self.width() * 0.42, 0)
        path.cubicTo(self.width() * 0.58, 22, self.width() * 0.7, 8, self.width() * 0.82, 36)
        path.lineTo(self.width() * 0.82, 0)
        path.closeSubpath()
        painter.drawPath(path)
        super().paintEvent(event)


class ProfileCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        self.avatar = QLabel()
        self.avatar.setFixedSize(56, 56)
        self._set_avatar()
        row.addWidget(self.avatar)
        col = QVBoxLayout()
        name = QLabel(settings.EMPLOYEE_NAME)
        name.setStyleSheet("font-size:16px; font-weight:700;")
        role = QLabel(settings.EMPLOYEE_ROLE)
        role.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        col.addWidget(name)
        col.addWidget(role)
        row.addLayout(col, 1)

    def _set_avatar(self) -> None:
        path = settings.PROFILE_PIC
        if os.path.isfile(path):
            src = QImage(path).convertToFormat(QImage.Format.Format_ARGB32)
            size = 56
            scaled = QPixmap.fromImage(src).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            out = QPixmap(size, size)
            out.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            painter.drawPixmap(-x, -y, scaled)
            painter.end()
            self.avatar.setPixmap(out)
        else:
            self.avatar.setText("SU")
            self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.avatar.setStyleSheet(
                f"background:{theme.PRIMARY}; color:white; border-radius:28px; font-weight:700;"
            )


class DashboardPage(QWidget):
    start_break = Signal()
    end_break = Signal()
    export_csv = Signal()
    summary = Signal()
    logout = Signal()
    camera_selected = Signal(str)
    toggle_camera = Signal(bool)
    stay_present = Signal()
    note_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = DashboardHeader()
        root.addWidget(self.header)

        self.reminder = ReminderBanner()
        self.reminder.stay_requested.connect(self.stay_present.emit)
        root.addWidget(self.reminder)

        self.break_banner = BreakBanner()
        self.break_banner.end_requested.connect(self.end_break.emit)
        root.addWidget(self.break_banner)

        content = QHBoxLayout()
        content.setContentsMargins(18, 14, 18, 10)
        content.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(ProfileCard())

        note_label = QLabel("Shift note")
        note_label.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        left.addWidget(note_label)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setObjectName("shiftNote")
        self.note_edit.setPlaceholderText("What I worked on today…")
        self.note_edit.setFixedHeight(54)
        self.note_edit.setTabChangesFocus(True)
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.setInterval(800)
        self._note_timer.timeout.connect(self._emit_note)
        self.note_edit.textChanged.connect(self._note_timer.start)
        left.addWidget(self.note_edit)

        overview = QLabel("Shift overview")
        overview.setStyleSheet("font-size:14px; font-weight:700;")
        left.addWidget(overview)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.card_login = StatCard("Login time", "--", theme.PRIMARY, "clock")
        self.card_shift = StatCard("On shift", "00:00:00", theme.SUCCESS, "timer")
        self.card_breaks = StatCard("Breaks", "00:00:00", theme.ORANGE, "coffee")
        self.card_worked = StatCard("Worked", "00:00:00", theme.PURPLE, "chart")
        grid.addWidget(self.card_login, 0, 0)
        grid.addWidget(self.card_shift, 0, 1)
        grid.addWidget(self.card_breaks, 1, 0)
        grid.addWidget(self.card_worked, 1, 1)
        left.addLayout(grid)

        self.break_log = BreakLogTable()
        left.addWidget(self.break_log, 1)
        content.addLayout(left, 3)

        right = QVBoxLayout()
        self.camera = CameraWidget(helper="Stay in view to avoid auto absence breaks.")
        self.camera.camera_selected.connect(self.camera_selected.emit)
        right.addWidget(self.camera)
        self.hide_cam_btn = PrimaryButton("Hide camera", kind="ghost")
        self.hide_cam_btn.setMinimumHeight(36)
        self._cam_visible = True
        self.hide_cam_btn.clicked.connect(self._toggle_cam)
        right.addWidget(self.hide_cam_btn, 0, Qt.AlignmentFlag.AlignLeft)
        tip = QLabel("Stay in view to avoid auto absence breaks.")
        tip.setStyleSheet(f"color:{theme.MUTED}; font-size:12px;")
        tip.setWordWrap(True)
        right.addWidget(tip)
        right.addStretch(1)
        content.addLayout(right, 2)

        content_host = QWidget()
        content_host.setLayout(content)
        root.addWidget(content_host, 1)

        bar = QFrame()
        bar.setObjectName("card")
        bar.setStyleSheet(
            f"QFrame#card {{ background:white; border:none; border-top:1px solid {theme.BORDER}; border-radius:0; }}"
        )
        bar.setFixedHeight(64)
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(18, 10, 18, 10)
        self.break_btn = PrimaryButton("Start break", kind="primary")
        self.break_btn.clicked.connect(self._on_break_clicked)
        bar_row.addWidget(self.break_btn)
        bar_row.addStretch()
        self.export_btn = PrimaryButton("Export CSV", kind="ghost")
        self.export_btn.setIcon(svg_icon("export", 16))
        self.export_btn.clicked.connect(self.export_csv.emit)
        self.summary_btn = PrimaryButton("Summary", kind="ghost")
        self.summary_btn.setIcon(svg_icon("chart", 16))
        self.summary_btn.clicked.connect(self.summary.emit)
        self.logout_btn = PrimaryButton("Logout", kind="danger")
        self.logout_btn.setIcon(svg_icon("logout", 16))
        self.logout_btn.clicked.connect(self.logout.emit)
        bar_row.addWidget(self.export_btn)
        bar_row.addWidget(self.summary_btn)
        bar_row.addWidget(self.logout_btn)
        root.addWidget(bar)
        self._on_break = False

    def _emit_note(self) -> None:
        self.note_changed.emit(self.note_edit.toPlainText())

    def set_shift_note(self, text: str) -> None:
        self.note_edit.blockSignals(True)
        self.note_edit.setPlainText(text or "")
        self.note_edit.blockSignals(False)

    def shift_note(self) -> str:
        return self.note_edit.toPlainText().strip()

    def _toggle_cam(self) -> None:
        self._cam_visible = not self._cam_visible
        self.camera.set_preview_visible(self._cam_visible)
        self.hide_cam_btn.setText("Show camera" if not self._cam_visible else "Hide camera")
        self.toggle_camera.emit(self._cam_visible)

    def _on_break_clicked(self) -> None:
        if self._on_break:
            self.end_break.emit()
        else:
            self.start_break.emit()

    def set_break_active(
        self,
        active: bool,
        label: str | None = None,
        start_time: datetime | None = None,
        *,
        face_resume: bool = False,
    ) -> None:
        self._on_break = active
        display = None
        if label:
            display = "Idle Sitting" if label == "Inactivity Only" else label
        self.header.status.set_status("on_break" if active else "on_shift", detail=display)
        if active:
            self.reminder.hide_warning()
            self.break_btn.setText("End break" + (f" — {display}" if display else ""))
            self.break_btn.setObjectName("dangerBtn")
            if start_time is not None:
                self.break_banner.start(
                    label or "Break",
                    start_time,
                    face_resume=face_resume,
                )
        else:
            self.break_btn.setText("Start break")
            self.break_btn.setObjectName("primaryBtn")
            self.break_banner.stop()
        self.break_btn.style().unpolish(self.break_btn)
        self.break_btn.style().polish(self.break_btn)

    def update_stats(self, snap: dict) -> None:
        self.card_login.set_value(snap.get("login_time", "--"))
        self.card_shift.set_value(snap.get("on_shift", "00:00:00"))
        self.card_breaks.set_value(snap.get("breaks", "00:00:00"))
        self.card_worked.set_value(snap.get("worked", "00:00:00"))

    def update_breaks(self, entries: list[list]) -> None:
        self.break_log.set_breaks(entries)
